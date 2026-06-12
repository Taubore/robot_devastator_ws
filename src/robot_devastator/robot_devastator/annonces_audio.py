"""Capacité audio unique du robot Devastator avec Piper et aplay."""

from collections.abc import Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import random
import signal
import subprocess
import time
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
DELAI_REVEIL_EXECUTEUR_S: Final[float] = 0.2
AUDIO_CACHE_DIR: Final[Path] = Path.home() / '.cache' / 'robot_devastator' / 'audio'

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
        self.repertoire_audio = AUDIO_CACHE_DIR
        self.annonces = self._charger_annonces()
        self.derniere_lecture_s: dict[str, float] = {}
        self.processus_externe_actif: subprocess.Popen[str] | None = None

        self._valider_parametres()
        self.repertoire_audio.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(f'Cache audio persistant utilisé : {self.repertoire_audio}.')

        # La préparation est volontairement synchrone : le nœud ne commence à écouter
        # /robot/evenement qu'après avoir préparé les fichiers ou journalisé les échecs.
        if self.preparer_audio_au_demarrage:
            self.preparer_annonces_audio()
        else:
            self.get_logger().warn(
                'Préparation audio au démarrage désactivée par paramètre.'
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
        """Prépare chaque fichier WAV configuré sans empêcher le robot de se lancer."""
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

    def arreter_processus_externe_actif(self) -> None:
        """Arrête la commande audio en cours, si le nœud est en lecture ou synthèse."""
        if self.processus_externe_actif is None:
            return

        self._terminer_processus_externe(self.processus_externe_actif)

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
        """Vérifie seulement les paramètres qui rendent la configuration incohérente."""
        if self.delai_min_repetition_s < 0.0:
            raise ValueError(
                "Le paramètre 'delai_min_repetition_s' ne peut pas être négatif."
            )
        if self.command_timeout_s <= 0.0:
            raise ValueError(
                "Le paramètre 'command_timeout_s' doit être strictement positif."
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
        # Fichier existe déjà, on s'arrête ici et on ne journalise rien.
        if chemin_audio.is_file():
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
            self.get_logger().info(f'Génération Piper demandée...')
            self._executer_commande_externe(
                commande,
                entree=variante.texte,
            )
            if not chemin_audio.is_file():
                self.get_logger().error(
                    f'Génération échouée pour {chemin_audio.name} : fichier non créé.'
                )
                return
            self.get_logger().info(f'Fichier audio généré : {chemin_audio.name}.')
        except subprocess.TimeoutExpired:
            self.get_logger().error(
                f'Génération échouée pour {chemin_audio.name} : Piper a dépassé '
                'le délai maximal.'
            )
        except subprocess.CalledProcessError as erreur:
            self.get_logger().error(
                f'Génération échouée pour {chemin_audio.name} : erreur Piper '
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
        """Joue un WAV du cache avec aplay et journalise les échecs sans lever."""
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

        try:
            self._executer_commande_externe(['aplay', str(chemin_audio)])
            self.get_logger().info(f'Lecture audio réussie : {chemin_audio.name}.')
        except subprocess.TimeoutExpired:
            self.get_logger().error(
                f'Lecture audio échouée pour {chemin_audio.name} : aplay a dépassé '
                'le délai maximal.'
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

    def _executer_commande_externe(
        self,
        commande: Sequence[str],
        *,
        entree: str | None = None,
    ) -> None:
        """Exécute une commande bloquante en gardant la fermeture interruptible."""
        processus = subprocess.Popen(
            commande,
            stdin=subprocess.PIPE if entree is not None else None,
            text=True,
            start_new_session=True,
        )
        self.processus_externe_actif = processus

        try:
            processus.communicate(input=entree, timeout=self.command_timeout_s)
            if processus.returncode:
                raise subprocess.CalledProcessError(processus.returncode, commande)
        except subprocess.TimeoutExpired:
            self._terminer_processus_externe(processus)
            raise
        except KeyboardInterrupt:
            self._terminer_processus_externe(processus)
            raise
        finally:
            if self.processus_externe_actif is processus:
                self.processus_externe_actif = None

    def _terminer_processus_externe(
        self,
        processus: subprocess.Popen[str],
    ) -> None:
        """Termine la commande externe active avant de laisser le nœud quitter."""
        if processus.poll() is not None:
            return

        try:
            os.killpg(processus.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except Exception:
            processus.terminate()

        try:
            processus.wait(timeout=2.0)
            return
        except subprocess.TimeoutExpired:
            pass

        try:
            os.killpg(processus.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except Exception:
            processus.kill()

        try:
            processus.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            self.get_logger().error(
                'La commande audio externe ne répond pas même après SIGKILL.'
            )

    # --- Cycle de vie du nœud ---


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2, prépare les fichiers WAV, puis écoute les événements."""
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, _interrompre_execution)
    signal.signal(signal.SIGTERM, _interrompre_execution)

    node: AnnoncesAudio | None = None
    try:
        node = AnnoncesAudio()
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=DELAI_REVEIL_EXECUTEUR_S)
    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().info("Arrêt demandé par l'utilisateur.")
    finally:
        try:
            if node is not None:
                node.arreter_processus_externe_actif()
                node.destroy_node()
        finally:
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == '__main__':
    main()
