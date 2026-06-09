"""Arbitre la source active des commandes moteur de Devastator."""

from __future__ import annotations

import signal
from time import monotonic
from types import FrameType
from typing import Final

from commun.msg import ConsigneMoteurs
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String

MODE_AUTONOMIE: Final[str] = 'autonomie'
MODE_MANUEL: Final[str] = 'manuel'
TAILLE_FILE_MESSAGES: Final[int] = 10
TOPIC_COMMANDE_AUTONOMIE: Final[str] = '/robot/commande_moteurs/autonomie'
TOPIC_COMMANDE_MANUELLE: Final[str] = '/robot/commande_moteurs/manuelle'
TOPIC_COMMANDE_PICO: Final[str] = '/pico/commande_moteurs'
TOPIC_MODE_CONDUITE: Final[str] = '/robot/mode_conduite'
VALEUR_MOTEUR_MAX: Final[int] = 1000
VALEUR_MOTEUR_MIN: Final[int] = -1000


def _interrompre_execution(
    _numero_signal: int,
    _frame: FrameType | None,
) -> None:
    """Interrompt proprement l'exécution lors d'une demande d'arrêt système."""
    raise KeyboardInterrupt


class ArbitreCommandeMoteurs(Node):
    """
    Publie une seule commande moteur vers le Pico selon le mode de conduite actif.
    """

    def __init__(self) -> None:
        super().__init__('arbitre_commande_moteurs')

        self.declare_parameter('mode_initial', MODE_MANUEL)
        self.declare_parameter('periode_publication_s', 0.1)
        self.declare_parameter('delai_expiration_source_s', 0.35)

        self.mode_actif = str(self.get_parameter('mode_initial').value)
        self.periode_publication_s = float(
            self.get_parameter('periode_publication_s').value
        )
        self.delai_expiration_source_s = float(
            self.get_parameter('delai_expiration_source_s').value
        )

        if self.mode_actif not in (MODE_MANUEL, MODE_AUTONOMIE):
            raise ValueError(
                "Le paramètre 'mode_initial' doit être 'manuel' ou 'autonomie'."
            )
        if self.periode_publication_s <= 0.0:
            raise ValueError("Le paramètre 'periode_publication_s' doit être positif.")
        if self.delai_expiration_source_s <= 0.0:
            raise ValueError(
                "Le paramètre 'delai_expiration_source_s' doit être positif."
            )

        self.derniere_consigne_manuelle = self._creer_consigne_arret()
        self.derniere_consigne_autonomie = self._creer_consigne_arret()
        self.derniere_reception_manuelle_s = 0.0
        self.derniere_reception_autonomie_s = 0.0

        self.consigne_pico_pub = self.create_publisher(
            ConsigneMoteurs,
            TOPIC_COMMANDE_PICO,
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_consigne_manuelle = self.create_subscription(
            ConsigneMoteurs,
            TOPIC_COMMANDE_MANUELLE,
            self._recevoir_consigne_manuelle_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_consigne_autonomie = self.create_subscription(
            ConsigneMoteurs,
            TOPIC_COMMANDE_AUTONOMIE,
            self._recevoir_consigne_autonomie_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_mode = self.create_subscription(
            String,
            TOPIC_MODE_CONDUITE,
            self._recevoir_mode_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.timer_publication = self.create_timer(
            self.periode_publication_s,
            self._publier_commande_active_callback,
        )

        self.get_logger().info(
            f'Arbitre de commandes moteur démarré en mode {self.mode_actif}.'
        )

    def arreter_moteurs(self) -> None:
        """Publie une commande d'arrêt explicite vers le Pico."""
        self._publier_consigne(self._creer_consigne_arret())

    # --- Callbacks des subscriptions ---

    def _recevoir_consigne_manuelle_callback(self, message: ConsigneMoteurs) -> None:
        """Mémorise la dernière commande reçue de la téléopération clavier."""
        self.derniere_consigne_manuelle = self._borner_consigne(message)
        self.derniere_reception_manuelle_s = monotonic()

    def _recevoir_consigne_autonomie_callback(self, message: ConsigneMoteurs) -> None:
        """Mémorise la dernière commande reçue du comportement autonome."""
        self.derniere_consigne_autonomie = self._borner_consigne(message)
        self.derniere_reception_autonomie_s = monotonic()

    def _recevoir_mode_callback(self, message: String) -> None:
        """Change la source active seulement pour un mode connu."""
        mode = message.data.strip().lower()
        if mode not in (MODE_MANUEL, MODE_AUTONOMIE):
            self.get_logger().warn(f'Mode de conduite ignoré : {message.data}.')
            return

        if mode != self.mode_actif:
            self.mode_actif = mode
            self.arreter_moteurs()
            self.get_logger().info(f'Mode de conduite actif : {self.mode_actif}.')

    # --- Callbacks des timers ---

    def _publier_commande_active_callback(self) -> None:
        """Publie la commande de la source active, ou un arrêt si elle est expirée."""
        maintenant_s = monotonic()

        if self.mode_actif == MODE_MANUEL:
            consigne = self.derniere_consigne_manuelle
            derniere_reception_s = self.derniere_reception_manuelle_s
        else:
            consigne = self.derniere_consigne_autonomie
            derniere_reception_s = self.derniere_reception_autonomie_s

        if maintenant_s - derniere_reception_s > self.delai_expiration_source_s:
            consigne = self._creer_consigne_arret()

        self._publier_consigne(consigne)

    # --- Méthodes privées utilitaires ---

    def _borner_consigne(self, message: ConsigneMoteurs) -> ConsigneMoteurs:
        """Retourne une copie de la consigne limitée à la plage moteur autorisée."""
        consigne = ConsigneMoteurs()
        consigne.gauche = self._borner_valeur_moteur(int(message.gauche))
        consigne.droite = self._borner_valeur_moteur(int(message.droite))
        return consigne

    def _borner_valeur_moteur(self, valeur: int) -> int:
        """Limite une valeur moteur entre les bornes acceptées par le Pico."""
        valeur_bornee = max(VALEUR_MOTEUR_MIN, min(VALEUR_MOTEUR_MAX, valeur))
        if valeur_bornee != valeur:
            self.get_logger().warn(
                f'Consigne moteur bornée de {valeur} à {valeur_bornee}.'
            )
        return valeur_bornee

    def _publier_consigne(self, consigne: ConsigneMoteurs) -> None:
        """Publie la consigne retenue vers le Pico."""
        self.consigne_pico_pub.publish(consigne)

    def _creer_consigne_arret(self) -> ConsigneMoteurs:
        """Crée une consigne d'arrêt moteur."""
        consigne = ConsigneMoteurs()
        consigne.gauche = 0
        consigne.droite = 0
        return consigne


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2 et lance l'arbitre de commandes moteur."""
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, _interrompre_execution)
    signal.signal(signal.SIGTERM, _interrompre_execution)
    noeud = ArbitreCommandeMoteurs()

    try:
        rclpy.spin(noeud)
    except KeyboardInterrupt:
        noeud.get_logger().info("Arrêt demandé par l'utilisateur.")
    finally:
        try:
            noeud.arreter_moteurs()
        finally:
            try:
                noeud.destroy_node()
            finally:
                if rclpy.ok():
                    rclpy.shutdown()


if __name__ == '__main__':
    main()
