"""Orchestrateur léger des annonces audio du robot."""

from dataclasses import dataclass
import random
import time
from typing import Final

from commun.srv import GenererAudio, JouerAudio
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from robot_devastator.voix_piper import AUDIO_CACHE_DIR
from std_msgs.msg import String

TOPIC_EVENEMENT_ROBOT: Final[str] = '/robot/evenement'
SERVICE_GENERER_AUDIO: Final[str] = '/generer_audio'
SERVICE_JOUER_AUDIO: Final[str] = '/jouer_audio'
TAILLE_FILE_MESSAGES: Final[int] = 10
DELAI_ATTENTE_SERVICES_AUDIO_S: Final[float] = 10.0
SEPARATEUR_VARIANTE: Final[str] = '|'

# Cette liste fixe limite volontairement l'orchestrateur aux annonces utiles actuellement.
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
        for evenement in EVENEMENTS_ANNONCES:
            self.declare_parameter(f'annonces.{evenement}', Parameter.Type.STRING_ARRAY)

        self.delai_min_repetition_s = float(
            self.get_parameter('delai_min_repetition_s').value
        )
        if self.delai_min_repetition_s < 0.0:
            raise ValueError(
                "Le paramètre 'delai_min_repetition_s' ne peut pas être négatif."
            )
        self.preparer_audio_au_demarrage = bool(
            self.get_parameter('preparer_audio_au_demarrage').value
        )
        self.jouer_annonce_demarrage = bool(
            self.get_parameter('jouer_annonce_demarrage').value
        )
        self.annonces = self._charger_annonces()
        self.derniere_lecture_s: dict[str, float] = {}

        self.generer_audio_cli = self.create_client(GenererAudio, SERVICE_GENERER_AUDIO)
        self.jouer_audio_cli = self.create_client(JouerAudio, SERVICE_JOUER_AUDIO)
        self.abonnement_evenement = self.create_subscription(
            String,
            TOPIC_EVENEMENT_ROBOT,
            self._recevoir_evenement_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.get_logger().info(f'Cache audio persistant utilisé : {AUDIO_CACHE_DIR}.')

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
                noms_fichiers.add(nom_fichier)
                variantes.append(VarianteAnnonce(nom_fichier, texte))
            annonces[evenement] = variantes
        return annonces

    def attendre_services_audio(self) -> bool:
        """Attend les deux services audio pendant un délai borné."""
        echeance = time.monotonic() + DELAI_ATTENTE_SERVICES_AUDIO_S
        for client, nom_service in (
            (self.generer_audio_cli, SERVICE_GENERER_AUDIO),
            (self.jouer_audio_cli, SERVICE_JOUER_AUDIO),
        ):
            while not client.wait_for_service(timeout_sec=1.0):
                if time.monotonic() >= echeance:
                    self.get_logger().error(
                        f"Service '{nom_service}' indisponible après "
                        f'{DELAI_ATTENTE_SERVICES_AUDIO_S:.0f} s.'
                    )
                    return False
                self.get_logger().warn(
                    f"Service '{nom_service}' indisponible, nouvelle tentative..."
                )
        self.get_logger().info('Services audio disponibles.')
        return True

    def preparer_annonces_audio(self) -> None:
        """Demande la génération préalable de chaque fichier WAV encore manquant."""
        for variantes in self.annonces.values():
            for variante in variantes:
                if variante is None:
                    continue
                chemin_audio = AUDIO_CACHE_DIR / f'{variante.nom_fichier}.wav'
                if chemin_audio.is_file():
                    self.get_logger().info(f'Fichier audio déjà présent : {chemin_audio}.')
                    continue
                self.get_logger().info(f'Fichier audio manquant : {chemin_audio}.')
                self._generer_audio(variante)

    def _generer_audio(self, variante: VarianteAnnonce) -> None:
        """Génère une variante manquante et journalise le résultat du service."""
        requete = GenererAudio.Request()
        requete.nom_fichier = variante.nom_fichier
        requete.texte = variante.texte
        self.get_logger().info(f'Génération demandée : {variante.nom_fichier}.wav.')
        future = self.generer_audio_cli.call_async(requete)
        rclpy.spin_until_future_complete(self, future)
        reponse = future.result()
        if reponse is None or not reponse.succes:
            message = reponse.message if reponse is not None else 'aucune réponse'
            self.get_logger().error(
                f'Génération échouée pour {variante.nom_fichier}.wav : {message}'
            )
            return
        self.get_logger().info(
            f'Génération réussie pour {variante.nom_fichier}.wav : '
            f'{reponse.chemin_fichier}'
        )

    def _recevoir_evenement_callback(self, message: String) -> None:
        """Choisit une variante et demande sa lecture sans bloquer l'orchestrateur."""
        self.jouer_annonce(message.data)

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

        if not self.jouer_audio_cli.service_is_ready():
            self.get_logger().warn(
                f"Annonce ignorée car le service '{SERVICE_JOUER_AUDIO}' "
                'est indisponible.'
            )
            return

        requete = JouerAudio.Request()
        requete.nom_fichier = variante.nom_fichier
        self.derniere_lecture_s[evenement] = maintenant_s
        future = self.jouer_audio_cli.call_async(requete)
        future.add_done_callback(
            lambda resultat, nom=variante.nom_fichier: self._journaliser_lecture(
                nom,
                resultat,
            )
        )

    def _journaliser_lecture(self, nom_fichier: str, future) -> None:
        """Journalise la réponse asynchrone du service de lecture audio."""
        try:
            reponse = future.result()
        except Exception as erreur:
            self.get_logger().error(
                f'Lecture audio échouée pour {nom_fichier}.wav : {erreur}'
            )
            return
        if reponse is None or not reponse.succes:
            message = reponse.message if reponse is not None else 'aucune réponse'
            self.get_logger().error(
                f'Lecture audio échouée pour {nom_fichier}.wav : {message}'
            )
            return
        self.get_logger().info(f'Lecture audio réussie : {nom_fichier}.wav.')


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2, prépare les fichiers WAV, puis écoute les événements."""
    rclpy.init(args=args)
    node = AnnoncesAudio()
    try:
        services_disponibles = node.attendre_services_audio()
        if services_disponibles and node.preparer_audio_au_demarrage:
            node.preparer_annonces_audio()
        if services_disponibles and node.jouer_annonce_demarrage:
            node.jouer_annonce('demarrage')
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Arrêt demandé par l'utilisateur.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
