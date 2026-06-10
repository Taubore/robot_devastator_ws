"""Capacité audio unique du robot Devastator avec Piper et aplay."""

from dataclasses import dataclass
from pathlib import Path
import random
import signal
import subprocess
import time
import wave
from types import FrameType
from typing import Final

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String

TOPIC_EVENEMENT_ROBOT: Final[str] = '/robot/evenement'
TAILLE_FILE_MESSAGES: Final[int] = 10
SEPARATEUR_VARIANTE: Final[str] = '|'
DEFAULT_PIPER_EXECUTABLE: Final[str] = '/usr/local/bin/piper'
DEFAULT_PIPER_MODEL: Final[str] = '/opt/piper/voix/fr_FR-siwis-low.onnx'
DEFAULT_PIPER_CONFIG: Final[str] = '/opt/piper/voix/fr_FR-siwis-low.onnx.json'
DEFAULT_COMMAND_TIMEOUT_S: Final[float] = 15.0
AUDIO_CACHE_DIR: Final[Path] = Path.home() / '.cache' / 'robot_devastator' / 'audio'
DEFAULT_GPIO_SD_AMPLI: Final[int] = 23
DEFAULT_FREQUENCE_AUDIO_HZ: Final[int] = 16000
DEFAULT_CANAUX_AUDIO: Final[int] = 1
DEFAULT_LARGEUR_ECHANTILLON_OCTETS: Final[int] = 2
DEFAULT_SILENCE_INITIAL_S: Final[float] = 1.0
DEFAULT_SILENCE_FIN_ANNONCE_S: Final[float] = 0.3

# Cette liste fixe limite volontairement la capacité audio aux annonces utiles actuellement.
EVENEMENTS_ANNONCES: Final[tuple[str, ...]] = (
    'demarrage',
    'autonomie_demarre',
    'obstacle_detecte',
    'analyse_obstacle',
    'rotation_gauche',
    'rotation_droite',
    'recul_recuperation',
    'reprise_avance',
    'arret_robot',
)


def _interrompre_execution(
    _numero_signal: int,
    _frame: FrameType | None,
) -> None:
    """Interrompt proprement l'exécution lors d'une demande d'arrêt système."""
    raise KeyboardInterrupt


@dataclass(frozen=True)
class VarianteAnnonce:
    """Associe un fichier WAV persistant au texte utilisé pour le préparer."""

    nom_fichier: str
    texte: str


class AnnoncesAudio(Node):
    """Prépare les annonces audio et les joue selon les événements du robot."""

    def __init__(self) -> None:
        super().__init__('annonces_audio')
        self.declare_parameter('delai_min_repetition_s', 3.0)
        self.declare_parameter('preparer_audio_au_demarrage', True)
        self.declare_parameter('jouer_annonce_demarrage', True)
        self.declare_parameter('piper_executable', DEFAULT_PIPER_EXECUTABLE)
        self.declare_parameter('piper_model', DEFAULT_PIPER_MODEL)
        self.declare_parameter('piper_config', DEFAULT_PIPER_CONFIG)
        self.declare_parameter('command_timeout_s', DEFAULT_COMMAND_TIMEOUT_S)
        self.declare_parameter('lecteur_audio_persistant_active', True)
        self.declare_parameter('controle_ampli_active', True)
        self.declare_parameter('gpio_sd_ampli', DEFAULT_GPIO_SD_AMPLI)
        self.declare_parameter('frequence_audio_hz', DEFAULT_FREQUENCE_AUDIO_HZ)
        self.declare_parameter('canaux_audio', DEFAULT_CANAUX_AUDIO)
        self.declare_parameter(
            'largeur_echantillon_octets',
            DEFAULT_LARGEUR_ECHANTILLON_OCTETS,
        )
        self.declare_parameter('silence_initial_s', DEFAULT_SILENCE_INITIAL_S)
        self.declare_parameter('silence_fin_annonce_s', DEFAULT_SILENCE_FIN_ANNONCE_S)
        for evenement in EVENEMENTS_ANNONCES:
            self.declare_parameter(f'annonces.{evenement}', Parameter.Type.STRING_ARRAY)

        self.delai_min_repetition_s = float(
            self.get_parameter('delai_min_repetition_s').value
        )
        self.preparer_audio_au_demarrage = bool(
            self.get_parameter('preparer_audio_au_demarrage').value
        )
        self.jouer_annonce_demarrage = bool(
            self.get_parameter('jouer_annonce_demarrage').value
        )
        self.piper_executable = str(self.get_parameter('piper_executable').value)
        self.piper_model = str(self.get_parameter('piper_model').value)
        self.piper_config = str(self.get_parameter('piper_config').value)
        self.command_timeout_s = float(self.get_parameter('command_timeout_s').value)
        self.lecteur_audio_persistant_active = bool(
            self.get_parameter('lecteur_audio_persistant_active').value
        )
        self.controle_ampli_active = bool(
            self.get_parameter('controle_ampli_active').value
        )
        self.gpio_sd_ampli = int(self.get_parameter('gpio_sd_ampli').value)
        self.frequence_audio_hz = int(self.get_parameter('frequence_audio_hz').value)
        self.canaux_audio = int(self.get_parameter('canaux_audio').value)
        self.largeur_echantillon_octets = int(
            self.get_parameter('largeur_echantillon_octets').value
        )
        self.silence_initial_s = float(self.get_parameter('silence_initial_s').value)
        self.silence_fin_annonce_s = float(
            self.get_parameter('silence_fin_annonce_s').value
        )
        self.repertoire_audio = AUDIO_CACHE_DIR
        self.annonces = self._charger_annonces()
        self.derniere_lecture_s: dict[str, float] = {}
        self.processus_aplay_persistant: subprocess.Popen[bytes] | None = None
        self.chemin_gpio_sd: Path | None = None

        self._valider_parametres()
        self._initialiser_controle_ampli()
        self.repertoire_audio.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(f'Cache audio persistant utilisé : {self.repertoire_audio}.')

        # La préparation est volontairement synchrone : le nœud ne commence à écouter
        # /robot/evenement qu'après avoir préparé les fichiers ou journalisé les échecs.
        if self.preparer_audio_au_demarrage:
            self.preparer_annonces_audio()
        else:
            self.get_logger().warn(
                "Préparation audio au démarrage désactivée par paramètre."
            )

        if self.jouer_annonce_demarrage:
            self.jouer_annonce('demarrage')

        self.abonnement_evenement = self.create_subscription(
            String,
            TOPIC_EVENEMENT_ROBOT,
            self._recevoir_evenement_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.get_logger().info(
            f"Capacité audio prête ; écoute des événements sur '{TOPIC_EVENEMENT_ROBOT}'."
        )

    def preparer_annonces_audio(self) -> None:
        """Prépare chaque fichier WAV configuré."""
        self.get_logger().info('Préparation synchrone des annonces audio configurées.')
        for variantes in self.annonces.values():
            for variante in variantes:
                if variante is None:
                    continue
                self._generer_audio_si_absent(variante)
        self.get_logger().info('Préparation des annonces audio terminée.')

    def jouer_annonce(self, evenement: str) -> None:
        """Joue au plus une variante configurée pour l'événement reçu."""
        variantes = self.annonces.get(evenement, [])
        if not variantes:
            return

        maintenant_s = time.monotonic()
        derniere_lecture_s = self.derniere_lecture_s.get(evenement)
        if (
            derniere_lecture_s is not None
            and maintenant_s - derniere_lecture_s < self.delai_min_repetition_s
        ):
            self.get_logger().debug(f'Annonce ignorée car trop rapprochée : {evenement}.')
            return

        variante = random.choice(variantes)
        # Une variante silencieuse participe au tirage aléatoire sans lancer de lecture.
        if variante is None:
            self.get_logger().debug(f'Variante silencieuse choisie : {evenement}.')
            return

        self.derniere_lecture_s[evenement] = maintenant_s
        self._jouer_audio(variante.nom_fichier)

    # --- Callbacks des subscriptions ---

    def _recevoir_evenement_callback(self, message: String) -> None:
        """Choisit une variante et joue localement son fichier WAV."""
        self.jouer_annonce(message.data)

    # --- Méthodes privées utilitaires ---

    def _charger_annonces(self) -> dict[str, list[VarianteAnnonce | None]]:
        """Charge les variantes configurées ; une chaîne vide représente le silence."""
        annonces: dict[str, list[VarianteAnnonce | None]] = {}
        noms_fichiers: set[str] = set()
        for evenement in EVENEMENTS_ANNONCES:
            variantes: list[VarianteAnnonce | None] = []
            valeurs = self.get_parameter(f'annonces.{evenement}').value
            for valeur in valeurs:
                if not valeur:
                    variantes.append(None)
                    continue
                if SEPARATEUR_VARIANTE not in valeur:
                    raise ValueError(
                        f"Variante invalide pour '{evenement}' : séparateur "
                        f"'{SEPARATEUR_VARIANTE}' manquant."
                    )
                nom_fichier, texte = valeur.split(SEPARATEUR_VARIANTE, maxsplit=1)
                nom_fichier = nom_fichier.strip()
                texte = texte.strip()
                if not nom_fichier or not texte:
                    raise ValueError(
                        f"Variante invalide pour '{evenement}' : nom ou texte vide."
                    )
                if nom_fichier in noms_fichiers:
                    raise ValueError(f"Nom de fichier audio dupliqué : '{nom_fichier}'.")
                self._resoudre_chemin_audio(nom_fichier)
                noms_fichiers.add(nom_fichier)
                variantes.append(VarianteAnnonce(nom_fichier, texte))
            annonces[evenement] = variantes
        return annonces

    def _valider_parametres(self) -> None:
        """Valide seulement les paramètres qui rendent la configuration incohérente."""
        if self.delai_min_repetition_s < 0.0:
            raise ValueError(
                "Le paramètre 'delai_min_repetition_s' ne peut pas être négatif."
            )
        if self.command_timeout_s <= 0.0:
            raise ValueError(
                "Le paramètre 'command_timeout_s' doit être strictement positif."
            )
        if self.gpio_sd_ampli < 0:
            raise ValueError(
                "Le paramètre 'gpio_sd_ampli' ne peut pas être négatif."
            )
        if self.frequence_audio_hz <= 0:
            raise ValueError(
                "Le paramètre 'frequence_audio_hz' doit être strictement positif."
            )
        if self.canaux_audio <= 0:
            raise ValueError(
                "Le paramètre 'canaux_audio' doit être strictement positif."
            )
        if self.largeur_echantillon_octets <= 0:
            raise ValueError(
                "Le paramètre 'largeur_echantillon_octets' doit être strictement positif."
            )
        if self.silence_initial_s < 0.0:
            raise ValueError(
                "Le paramètre 'silence_initial_s' ne peut pas être négatif."
            )
        if self.silence_fin_annonce_s < 0.0:
            raise ValueError(
                "Le paramètre 'silence_fin_annonce_s' ne peut pas être négatif."
            )
        if not self.piper_executable.strip():
            self.get_logger().error(
                "Paramètre 'piper_executable' vide : les WAV manquants ne pourront pas "
                'être générés.'
            )
        if not self.piper_model.strip():
            self.get_logger().error(
                "Paramètre 'piper_model' vide : les WAV manquants ne pourront pas "
                'être générés.'
            )
        if not self.piper_config.strip():
            self.get_logger().warn(
                "Paramètre 'piper_config' vide : Piper sera appelé sans fichier "
                'de configuration séparé.'
            )

    def _resoudre_chemin_audio(self, nom_fichier: str) -> Path:
        """Retourne le chemin audio cible à partir d'un nom simple."""
        if '/' in nom_fichier or '\\' in nom_fichier:
            raise ValueError('Le nom de fichier doit être un nom simple, sans chemin.')
        return self.repertoire_audio / f'{nom_fichier}.wav'

    def _generer_audio_si_absent(self, variante: VarianteAnnonce) -> None:
        """Génère un WAV manquant avec Piper et journalise chaque résultat."""
        chemin_audio = self._resoudre_chemin_audio(variante.nom_fichier)
        if chemin_audio.is_file():
            self.get_logger().info(f'Fichier audio déjà présent : {chemin_audio.name}.')
            return

        if not self.piper_executable.strip() or not self.piper_model.strip():
            self.get_logger().error(
                f'Génération impossible pour {chemin_audio.name} : configuration Piper '
                'incomplète.'
            )
            return

        if not Path(self.piper_model).is_file():
            self.get_logger().error(
                f'Génération impossible pour {chemin_audio.name} : modèle Piper '
                f'introuvable ({self.piper_model}).'
            )
            return

        commande = [
            self.piper_executable,
            '--model', self.piper_model,
            '--output_file', str(chemin_audio),
        ]
        if self.piper_config.strip():
            if not Path(self.piper_config).is_file():
                self.get_logger().error(
                    f'Génération impossible pour {chemin_audio.name} : configuration '
                    f'Piper introuvable ({self.piper_config}).'
                )
                return
            commande.extend(['--config', self.piper_config])

        try:
            self.get_logger().info(f'Génération Piper demandée : {chemin_audio.name}.')
            subprocess.run(
                commande,
                input=variante.texte,
                text=True,
                check=True,
                timeout=self.command_timeout_s,
            )
            if not chemin_audio.is_file():
                self.get_logger().error(
                    f'Génération échouée pour {chemin_audio.name} : fichier non créé.'
                )
                return
            self.get_logger().info(f'Fichier audio généré : {chemin_audio.name}.')
        except subprocess.TimeoutExpired:
            self.get_logger().error(
                f"Génération échouée pour {chemin_audio.name} : Piper a dépassé "
                "le délai d'exécution."
            )
        except subprocess.CalledProcessError as erreur:
            self.get_logger().error(
                f"Génération échouée pour {chemin_audio.name} : erreur Piper "
                f'{erreur.returncode}.'
            )
        except FileNotFoundError:
            self.get_logger().error(
                f'Génération échouée pour {chemin_audio.name} : exécutable Piper '
                f'introuvable ({self.piper_executable}).'
            )
        except Exception as erreur:
            self.get_logger().error(
                f'Génération échouée pour {chemin_audio.name} : {erreur}'
            )

    def _jouer_audio(self, nom_fichier: str) -> None:
        """Joue un WAV du cache avec le lecteur persistant ou le repli ponctuel."""
        try:
            chemin_audio = self._resoudre_chemin_audio(nom_fichier)
        except ValueError as erreur:
            self.get_logger().error(
                f"Lecture audio impossible pour '{nom_fichier}' : {erreur}"
            )
            return

        if not chemin_audio.is_file():
            self.get_logger().error(
                f"Impossible de jouer le fichier audio '{chemin_audio.name}' : "
                f'fichier absent du cache ({chemin_audio}).'
            )
            return

        donnees_pcm = self._lire_frames_pcm_valides(chemin_audio)
        if donnees_pcm is None:
            return

        if self.lecteur_audio_persistant_active:
            if self._jouer_audio_persistant(chemin_audio, donnees_pcm):
                return
            self.get_logger().warn(
                f'Repli vers la lecture ponctuelle aplay pour {chemin_audio.name}.'
            )

        self._jouer_audio_ponctuel(chemin_audio)

    def _lire_frames_pcm_valides(self, chemin_audio: Path) -> bytes | None:
        """Lit les frames PCM seulement si le WAV correspond au format attendu."""
        try:
            with wave.open(str(chemin_audio), 'rb') as fichier_wav:
                compression = fichier_wav.getcomptype()
                canaux = fichier_wav.getnchannels()
                frequence = fichier_wav.getframerate()
                largeur = fichier_wav.getsampwidth()
                frames = fichier_wav.getnframes()

                if (
                    compression != 'NONE'
                    or canaux != self.canaux_audio
                    or frequence != self.frequence_audio_hz
                    or largeur != self.largeur_echantillon_octets
                ):
                    self.get_logger().error(
                        f'Annonce ignorée pour {chemin_audio.name} : format WAV '
                        f'inattendu ({compression=}, {canaux=}, {frequence=}, '
                        f'{largeur=}). Format attendu : PCM, '
                        f'{self.canaux_audio} canal(aux), '
                        f'{self.frequence_audio_hz} Hz, '
                        f'{self.largeur_echantillon_octets * 8} bits.'
                    )
                    return None

                return fichier_wav.readframes(frames)
        except wave.Error as erreur:
            self.get_logger().error(
                f'Annonce ignorée pour {chemin_audio.name} : WAV illisible ({erreur}).'
            )
        except OSError as erreur:
            self.get_logger().error(
                f'Annonce ignorée pour {chemin_audio.name} : lecture impossible ({erreur}).'
            )
        return None

    def _jouer_audio_persistant(self, chemin_audio: Path, donnees_pcm: bytes) -> bool:
        """Écrit les données PCM dans le flux aplay raw gardé ouvert."""
        if not self._assurer_lecteur_persistant():
            return False

        processus = self.processus_aplay_persistant
        if processus is None or processus.stdin is None:
            return False

        if processus.poll() is not None:
            self.get_logger().error(
                f'Lecteur audio persistant arrêté avant {chemin_audio.name} '
                f'(code {processus.returncode}).'
            )
            self.processus_aplay_persistant = None
            return False

        try:
            processus.stdin.write(donnees_pcm)
            processus.stdin.write(self._creer_silence_pcm(self.silence_fin_annonce_s))
            processus.stdin.flush()
            self.get_logger().info(f'Lecture audio persistante réussie : {chemin_audio.name}.')
            return True
        except BrokenPipeError:
            self.get_logger().error(
                f'Lecture audio persistante échouée pour {chemin_audio.name} : '
                'flux aplay fermé.'
            )
        except OSError as erreur:
            self.get_logger().error(
                f'Lecture audio persistante échouée pour {chemin_audio.name} : {erreur}'
            )

        self._fermer_lecteur_persistant(remettre_sd_bas=False)
        return False

    def _assurer_lecteur_persistant(self) -> bool:
        """Démarre aplay raw une seule fois et conserve son stdin ouvert."""
        if self.processus_aplay_persistant is not None:
            if self.processus_aplay_persistant.poll() is None:
                return True
            self.get_logger().error(
                'Lecteur audio persistant arrêté avec le code '
                f'{self.processus_aplay_persistant.returncode}.'
            )
            self.processus_aplay_persistant = None

        commande = [
            'aplay',
            '-q',
            '-f', 'S16_LE',
            '-c', str(self.canaux_audio),
            '-r', str(self.frequence_audio_hz),
            '-t', 'raw',
        ]

        try:
            self._definir_sd_ampli(True)
            self.processus_aplay_persistant = subprocess.Popen(
                commande,
                stdin=subprocess.PIPE,
            )
            if self.processus_aplay_persistant.stdin is None:
                raise RuntimeError('stdin du lecteur persistant indisponible')
            self.processus_aplay_persistant.stdin.write(
                self._creer_silence_pcm(self.silence_initial_s)
            )
            self.processus_aplay_persistant.stdin.flush()
            self.get_logger().info('Lecteur audio persistant démarré en mode raw.')
            return True
        except FileNotFoundError:
            self.get_logger().error('Lecteur audio persistant indisponible : aplay introuvable.')
        except Exception as erreur:
            self.get_logger().error(
                f'Lecteur audio persistant indisponible : {erreur}'
            )

        self._fermer_lecteur_persistant(remettre_sd_bas=False)
        return False

    def _jouer_audio_ponctuel(self, chemin_audio: Path) -> None:
        """Joue un WAV avec l'ancien mode aplay fichier, utilisé comme repli."""
        try:
            subprocess.run(
                ['aplay', str(chemin_audio)],
                check=True,
                timeout=self.command_timeout_s,
            )
            self.get_logger().info(f'Lecture audio ponctuelle réussie : {chemin_audio.name}.')
        except subprocess.TimeoutExpired:
            self.get_logger().error(
                f"Lecture audio échouée pour {chemin_audio.name} : aplay a dépassé "
                "le délai d'exécution."
            )
        except subprocess.CalledProcessError as erreur:
            self.get_logger().error(
                f'Lecture audio échouée pour {chemin_audio.name} : erreur aplay '
                f'{erreur.returncode}.'
            )
        except FileNotFoundError:
            self.get_logger().error(
                f'Lecture audio échouée pour {chemin_audio.name} : aplay introuvable.'
            )
        except Exception as erreur:
            self.get_logger().error(
                f'Lecture audio échouée pour {chemin_audio.name} : {erreur}'
            )

    def _creer_silence_pcm(self, duree_s: float) -> bytes:
        """Crée un bloc de silence PCM brut adapté au format audio configuré."""
        nombre_frames = max(0, int(self.frequence_audio_hz * duree_s))
        octets_par_frame = self.canaux_audio * self.largeur_echantillon_octets
        return b'\x00' * nombre_frames * octets_par_frame

    def _initialiser_controle_ampli(self) -> None:
        """Prépare le GPIO SD de l'ampli et le force au niveau bas au démarrage."""
        if not self.controle_ampli_active:
            self.get_logger().info('Contrôle SD de l’ampli audio désactivé par paramètre.')
            return

        chemin_gpio = Path('/sys/class/gpio') / f'gpio{self.gpio_sd_ampli}'
        try:
            if not chemin_gpio.exists():
                Path('/sys/class/gpio/export').write_text(str(self.gpio_sd_ampli))
            direction = chemin_gpio / 'direction'
            valeur = chemin_gpio / 'value'
            limite_s = time.monotonic() + 1.0
            while not direction.exists() and time.monotonic() < limite_s:
                time.sleep(0.01)
            direction.write_text('out')
            valeur.write_text('0')
            self.chemin_gpio_sd = chemin_gpio
            self.get_logger().info(
                f'GPIO{self.gpio_sd_ampli} configuré pour SD ampli audio, niveau bas.'
            )
        except OSError as erreur:
            self.chemin_gpio_sd = None
            self.get_logger().error(
                f'Contrôle SD ampli indisponible sur GPIO{self.gpio_sd_ampli} : {erreur}'
            )

    def _definir_sd_ampli(self, actif: bool) -> None:
        """Place SD au niveau demandé sans interrompre le nœud en cas d'échec."""
        if not self.controle_ampli_active:
            return
        if self.chemin_gpio_sd is None:
            return

        try:
            (self.chemin_gpio_sd / 'value').write_text('1' if actif else '0')
        except OSError as erreur:
            self.get_logger().error(
                f'Impossible de définir SD ampli sur GPIO{self.gpio_sd_ampli} : {erreur}'
            )

    def _fermer_lecteur_persistant(self, remettre_sd_bas: bool = True) -> None:
        """Ferme le flux audio persistant sans faire échouer l'arrêt du nœud."""
        processus = self.processus_aplay_persistant
        self.processus_aplay_persistant = None

        if processus is not None:
            try:
                if processus.stdin is not None and processus.poll() is None:
                    processus.stdin.write(self._creer_silence_pcm(self.silence_fin_annonce_s))
                    processus.stdin.flush()
                    processus.stdin.close()
                processus.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.get_logger().warn('Arrêt du lecteur audio persistant forcé.')
                processus.terminate()
                try:
                    processus.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    processus.kill()
            except (BrokenPipeError, OSError) as erreur:
                self.get_logger().warn(
                    f'Fermeture du lecteur audio persistant incomplète : {erreur}'
                )

        if remettre_sd_bas:
            self._definir_sd_ampli(False)

    # --- Cycle de vie du nœud ---

    def destroy_node(self) -> bool:
        """Arrête le lecteur audio et coupe SD avant de détruire le nœud."""
        self._fermer_lecteur_persistant(remettre_sd_bas=True)
        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2, prépare les fichiers WAV, puis écoute les événements."""
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, _interrompre_execution)
    signal.signal(signal.SIGTERM, _interrompre_execution)

    node = AnnoncesAudio()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Arrêt demandé par l'utilisateur.")
    finally:
        try:
            node.destroy_node()
        finally:
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == '__main__':
    main()
