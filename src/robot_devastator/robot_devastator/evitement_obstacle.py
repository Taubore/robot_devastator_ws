"""Comportement minimal d'évitement d'obstacle pour Devastator."""

from __future__ import annotations

from typing import Final

from commun.msg import ConsigneMoteurs
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32

TOPIC_COMMANDE_MOTEURS: Final[str] = '/pico/commande_moteurs'
TOPIC_DISTANCE_ULTRASON: Final[str] = '/pico/distance_ultrason_mm'
VALEUR_MOTEUR_MIN: Final[int] = -1000
VALEUR_MOTEUR_MAX: Final[int] = 1000
TAILLE_FILE_MESSAGES: Final[int] = 10


class EvitementObstacle(Node):
    """Nœud d'autonomie v0 basé seulement sur la distance ultrason avant."""

    def __init__(self) -> None:
        super().__init__('evitement_obstacle_node')

        self.declare_parameter('distance_arret_mm', 350)
        self.declare_parameter('vitesse_avance', 500)
        self.declare_parameter('periode_publication_s', 0.1)
        self.declare_parameter('distance_invalide_arrete', True)

        self.distance_arret_mm = int(self.get_parameter('distance_arret_mm').value)
        self.vitesse_avance = int(self.get_parameter('vitesse_avance').value)
        self.periode_publication_s = float(
            self.get_parameter('periode_publication_s').value
        )
        self.distance_invalide_arrete = bool(
            self.get_parameter('distance_invalide_arrete').value
        )

        if self.distance_arret_mm <= 0:
            raise ValueError("Le paramètre 'distance_arret_mm' doit être positif.")
        if self.periode_publication_s <= 0.0:
            raise ValueError("Le paramètre 'periode_publication_s' doit être positif.")
        if not self.distance_invalide_arrete:
            self.get_logger().warn(
                "Le paramètre 'distance_invalide_arrete' est désactivé, mais cette "
                'version v0 reste arrêtée quand une distance invalide est reçue.'
            )

        self.vitesse_avance = self._borner_consigne_moteur(self.vitesse_avance)
        self.derniere_distance_mm: int | None = None

        self.consigne_moteurs_pub = self.create_publisher(
            ConsigneMoteurs,
            TOPIC_COMMANDE_MOTEURS,
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_distance = self.create_subscription(
            Int32,
            TOPIC_DISTANCE_ULTRASON,
            self._recevoir_distance,
            TAILLE_FILE_MESSAGES,
        )
        self.timer_publication = self.create_timer(
            self.periode_publication_s,
            self._publier_consigne_selon_distance,
        )

        self.get_logger().info(
            "Évitement d'obstacle v0 démarré: "
            f'distance_arret_mm={self.distance_arret_mm}, '
            f'vitesse_avance={self.vitesse_avance}.'
        )
        self.arreter_moteurs()

    def _borner_consigne_moteur(self, valeur: int) -> int:
        """Retourne une consigne limitée à la plage moteur autorisée."""
        valeur_bornee = max(VALEUR_MOTEUR_MIN, min(VALEUR_MOTEUR_MAX, valeur))
        if valeur_bornee != valeur:
            self.get_logger().warn(
                f'Consigne moteur bornée de {valeur} à {valeur_bornee}.'
            )
        return valeur_bornee

    def _recevoir_distance(self, message: Int32) -> None:
        """Mémorise la dernière distance valide reçue du Pico."""
        distance_mm = int(message.data)

        if distance_mm <= 0:
            self.get_logger().warn(
                f'Distance ultrason invalide reçue: {distance_mm} mm.'
            )
            self.derniere_distance_mm = None
            return

        self.derniere_distance_mm = distance_mm

    def _publier_consigne_selon_distance(self) -> None:
        """Publie avance lente ou arrêt selon la dernière distance connue."""
        if self.derniere_distance_mm is None:
            self.arreter_moteurs()
            return

        if self.derniere_distance_mm <= self.distance_arret_mm:
            self.arreter_moteurs()
            return

        self.publier_consigne_moteurs(self.vitesse_avance, self.vitesse_avance)

    def publier_consigne_moteurs(self, gauche: int, droite: int) -> None:
        """Publie une consigne moteur bornée vers l'interface Pico."""
        message = ConsigneMoteurs()
        message.gauche = self._borner_consigne_moteur(gauche)
        message.droite = self._borner_consigne_moteur(droite)
        self.consigne_moteurs_pub.publish(message)

    def arreter_moteurs(self) -> None:
        """Publie une consigne d'arrêt explicite."""
        self.publier_consigne_moteurs(0, 0)


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2 et exécute le comportement d'évitement minimal."""
    rclpy.init(args=args)
    node: EvitementObstacle | None = None

    try:
        node = EvitementObstacle()
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().info("Arrêt demandé par l'utilisateur.")
    finally:
        if node is not None:
            node.arreter_moteurs()
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
