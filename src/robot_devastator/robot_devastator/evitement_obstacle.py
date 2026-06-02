"""Comportement minimal d'évitement d'obstacle pour Devastator."""

from __future__ import annotations

from enum import auto, Enum
import signal
from time import monotonic
from types import FrameType
from typing import Final

from commun.msg import ConsigneMoteurs
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import Int32, String

TOPIC_COMMANDE_MOTEURS: Final[str] = '/pico/commande_moteurs'
TOPIC_COMMANDE_TOURELLE: Final[str] = '/pico/commande_tourelle_deg'
TOPIC_DISTANCE_ULTRASON: Final[str] = '/pico/distance_ultrason_mm'
TOPIC_EVENEMENT_ROBOT: Final[str] = '/robot/evenement'
VALEUR_MOTEUR_MIN: Final[int] = -1000
VALEUR_MOTEUR_MAX: Final[int] = 1000
ANGLE_TOURELLE_MIN_DEG: Final[int] = 0
ANGLE_TOURELLE_MAX_DEG: Final[int] = 180
TAILLE_FILE_MESSAGES: Final[int] = 10


def _interrompre_execution(
    _numero_signal: int,
    _frame: FrameType | None,
) -> None:
    """Interrompt proprement l'exécution lors d'une demande d'arrêt système."""
    raise KeyboardInterrupt


class EtatEvitement(Enum):
    """Étapes successives du comportement d'évitement."""

    AVANCE = auto()
    STABILISATION_GAUCHE = auto()
    MESURE_GAUCHE = auto()
    STABILISATION_CENTRE = auto()
    MESURE_CENTRE = auto()
    STABILISATION_DROITE = auto()
    MESURE_DROITE = auto()
    STABILISATION_ROTATION = auto()
    ROTATION = auto()
    RECUL = auto()
    RECENTRAGE = auto()
    VERIFICATION_REPRISE = auto()


class CoteRotation(Enum):
    """Côtés possibles pour la recherche de dégagement."""

    GAUCHE = auto()
    DROITE = auto()


class EvitementObstacle(Node):
    """Nœud d'autonomie simple basé sur une distance ultrason orientable."""

    def __init__(self) -> None:
        super().__init__('evitement_obstacle_node')

        self.declare_parameter('distance_arret_mm', 350)
        self.declare_parameter('vitesse_avance', 500)
        self.declare_parameter('periode_publication_s', 0.1)
        self.declare_parameter('angle_tourelle_centre_deg', 95)
        self.declare_parameter('angle_tourelle_gauche_deg', 45)
        self.declare_parameter('angle_tourelle_droite_deg', 140)
        self.declare_parameter('delai_stabilisation_tourelle_s', 0.35)
        self.declare_parameter('distance_degagement_mm', 600)
        self.declare_parameter('mesures_degagement_requises', 3)
        self.declare_parameter('vitesse_rotation_recherche', 300)
        self.declare_parameter('vitesse_recul', 300)
        self.declare_parameter('duree_rotation_recherche_min_s', 0.6)
        self.declare_parameter('duree_rotation_recherche_max_s', 4.0)
        self.declare_parameter('duree_recul_s', 0.45)
        self.declare_parameter('marge_choix_direction_mm', 120)

        self.distance_arret_mm = int(self.get_parameter('distance_arret_mm').value)
        self.vitesse_avance = int(self.get_parameter('vitesse_avance').value)
        self.periode_publication_s = float(
            self.get_parameter('periode_publication_s').value
        )
        self.angle_tourelle_centre_deg = int(
            self.get_parameter('angle_tourelle_centre_deg').value
        )
        self.angle_tourelle_gauche_deg = int(
            self.get_parameter('angle_tourelle_gauche_deg').value
        )
        self.angle_tourelle_droite_deg = int(
            self.get_parameter('angle_tourelle_droite_deg').value
        )
        self.delai_stabilisation_tourelle_s = float(
            self.get_parameter('delai_stabilisation_tourelle_s').value
        )
        self.distance_degagement_mm = int(
            self.get_parameter('distance_degagement_mm').value
        )
        self.mesures_degagement_requises = int(
            self.get_parameter('mesures_degagement_requises').value
        )
        self.vitesse_rotation_recherche = int(
            self.get_parameter('vitesse_rotation_recherche').value
        )
        self.vitesse_recul = int(self.get_parameter('vitesse_recul').value)
        self.duree_rotation_recherche_min_s = float(
            self.get_parameter('duree_rotation_recherche_min_s').value
        )
        self.duree_rotation_recherche_max_s = float(
            self.get_parameter('duree_rotation_recherche_max_s').value
        )
        self.duree_recul_s = float(self.get_parameter('duree_recul_s').value)
        self.marge_choix_direction_mm = int(
            self.get_parameter('marge_choix_direction_mm').value
        )

        if self.distance_arret_mm <= 0:
            raise ValueError("Le paramètre 'distance_arret_mm' doit être positif.")
        if self.periode_publication_s <= 0.0:
            raise ValueError("Le paramètre 'periode_publication_s' doit être positif.")
        if self.delai_stabilisation_tourelle_s < 0.0:
            raise ValueError(
                "Le paramètre 'delai_stabilisation_tourelle_s' ne peut pas être négatif."
            )
        if self.distance_degagement_mm <= 0:
            raise ValueError("Le paramètre 'distance_degagement_mm' doit être positif.")
        if self.mesures_degagement_requises <= 0:
            raise ValueError(
                "Le paramètre 'mesures_degagement_requises' doit être positif."
            )
        if self.duree_rotation_recherche_min_s < 0.0:
            raise ValueError(
                "Le paramètre 'duree_rotation_recherche_min_s' ne peut pas être négatif."
            )
        if self.duree_rotation_recherche_max_s <= self.duree_rotation_recherche_min_s:
            raise ValueError(
                "Le paramètre 'duree_rotation_recherche_max_s' doit être supérieur à "
                "'duree_rotation_recherche_min_s'."
            )
        if self.duree_recul_s <= 0.0:
            raise ValueError("Le paramètre 'duree_recul_s' doit être positif.")
        if self.marge_choix_direction_mm < 0:
            raise ValueError(
                "Le paramètre 'marge_choix_direction_mm' ne peut pas être négatif."
            )
        for nom, angle in (
            ('angle_tourelle_centre_deg', self.angle_tourelle_centre_deg),
            ('angle_tourelle_gauche_deg', self.angle_tourelle_gauche_deg),
            ('angle_tourelle_droite_deg', self.angle_tourelle_droite_deg),
        ):
            if not ANGLE_TOURELLE_MIN_DEG <= angle <= ANGLE_TOURELLE_MAX_DEG:
                raise ValueError(
                    f"Le paramètre '{nom}' doit être compris entre "
                    f'{ANGLE_TOURELLE_MIN_DEG} et {ANGLE_TOURELLE_MAX_DEG}.'
                )
        self.vitesse_avance = self._borner_consigne_moteur(self.vitesse_avance)
        self.vitesse_rotation_recherche = abs(
            self._borner_consigne_moteur(self.vitesse_rotation_recherche)
        )
        self.vitesse_recul = abs(self._borner_consigne_moteur(self.vitesse_recul))
        if self.vitesse_rotation_recherche == 0:
            raise ValueError(
                "Le paramètre 'vitesse_rotation_recherche' doit être différent de zéro."
            )
        if self.vitesse_recul == 0:
            raise ValueError("Le paramètre 'vitesse_recul' doit être différent de zéro.")
        self.derniere_distance_mm: int | None = None
        self.numero_derniere_distance = 0
        self.numero_distance_avant_mesure = 0
        self.distance_gauche_mm: int | None = None
        self.distance_droite_mm: int | None = None
        self.etat = EtatEvitement.AVANCE
        self.fin_etape_s = 0.0
        self.debut_validation_degagement_s = 0.0
        self.consigne_rotation: tuple[int, int] = (0, 0)
        self.dernier_cote_rotation = CoteRotation.GAUCHE
        self.nombre_mesures_degagement = 0

        self.consigne_moteurs_pub = self.create_publisher(
            ConsigneMoteurs,
            TOPIC_COMMANDE_MOTEURS,
            TAILLE_FILE_MESSAGES,
        )
        self.consigne_tourelle_pub = self.create_publisher(
            Int32,
            TOPIC_COMMANDE_TOURELLE,
            TAILLE_FILE_MESSAGES,
        )
        self.evenement_robot_pub = self.create_publisher(
            String,
            TOPIC_EVENEMENT_ROBOT,
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_distance = self.create_subscription(
            Int32,
            TOPIC_DISTANCE_ULTRASON,
            self._recevoir_distance_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.timer_publication = self.create_timer(
            self.periode_publication_s,
            self._publier_consigne_selon_distance_callback,
        )

        self.get_logger().info(
            "Évitement d'obstacle simple démarré : "
            f'distance_arret_mm={self.distance_arret_mm}, '
            f'vitesse_avance={self.vitesse_avance}.'
        )
        self.arreter_moteurs()
        self.publier_consigne_tourelle(self.angle_tourelle_centre_deg)
        self.publier_evenement('autonomie_demarre')

    def _borner_consigne_moteur(self, valeur: int) -> int:
        """Retourne une consigne limitée à la plage moteur autorisée."""
        valeur_bornee = max(VALEUR_MOTEUR_MIN, min(VALEUR_MOTEUR_MAX, valeur))
        if valeur_bornee != valeur:
            self.get_logger().warn(
                f'Consigne moteur bornée de {valeur} à {valeur_bornee}.'
            )
        return valeur_bornee

    def _recevoir_distance_callback(self, message: Int32) -> None:
        """Mémorise la dernière distance valide reçue du Pico."""
        distance_mm = int(message.data)
        self.numero_derniere_distance += 1

        if distance_mm <= 0:
            self.get_logger().warn(
                f'Distance ultrason invalide reçue : {distance_mm} mm.'
            )
            self.derniere_distance_mm = None
            self.nombre_mesures_degagement = 0
            return

        self.derniere_distance_mm = distance_mm
        if self.etat == EtatEvitement.ROTATION:
            if monotonic() < self.debut_validation_degagement_s:
                self.nombre_mesures_degagement = 0
                return
            if distance_mm >= self.distance_degagement_mm:
                self.nombre_mesures_degagement += 1
                if (
                    self.nombre_mesures_degagement
                    >= self.mesures_degagement_requises
                ):
                    self._commencer_recentrage()
            else:
                self.nombre_mesures_degagement = 0

    def _publier_consigne_selon_distance_callback(self) -> None:
        """Fait progresser l'évitement et publie une consigne moteur sécuritaire."""
        if self.etat == EtatEvitement.AVANCE:
            self._gerer_avance()
        elif self.etat == EtatEvitement.STABILISATION_GAUCHE:
            self._gerer_stabilisation(EtatEvitement.MESURE_GAUCHE)
        elif self.etat == EtatEvitement.MESURE_GAUCHE:
            self._gerer_mesure_gauche()
        elif self.etat == EtatEvitement.STABILISATION_CENTRE:
            self._gerer_stabilisation(EtatEvitement.MESURE_CENTRE)
        elif self.etat == EtatEvitement.MESURE_CENTRE:
            self._gerer_mesure_centre()
        elif self.etat == EtatEvitement.STABILISATION_DROITE:
            self._gerer_stabilisation(EtatEvitement.MESURE_DROITE)
        elif self.etat == EtatEvitement.MESURE_DROITE:
            self._gerer_mesure_droite()
        elif self.etat == EtatEvitement.STABILISATION_ROTATION:
            self._gerer_stabilisation_rotation()
        elif self.etat == EtatEvitement.ROTATION:
            self._gerer_rotation()
        elif self.etat == EtatEvitement.RECUL:
            self._gerer_recul()
        elif self.etat == EtatEvitement.RECENTRAGE:
            self._gerer_recentrage()
        elif self.etat == EtatEvitement.VERIFICATION_REPRISE:
            self._gerer_verification_reprise()

    def _gerer_avance(self) -> None:
        """Avance si la distance avant est valide et suffisante."""
        if self.derniere_distance_mm is None:
            self.arreter_moteurs()
            return

        if self.derniere_distance_mm <= self.distance_arret_mm:
            self.publier_evenement('obstacle_detecte')
            self._commencer_analyse_obstacle()
            return

        self.publier_consigne_moteurs(self.vitesse_avance, self.vitesse_avance)

    def _commencer_analyse_obstacle(self) -> None:
        """Arrête le robot et oriente la tourelle vers la gauche."""
        self.arreter_moteurs()
        self.distance_gauche_mm = None
        self.distance_droite_mm = None
        self.publier_consigne_tourelle(self.angle_tourelle_gauche_deg)
        self.fin_etape_s = monotonic() + self.delai_stabilisation_tourelle_s
        self.etat = EtatEvitement.STABILISATION_GAUCHE
        self.publier_evenement('analyse_obstacle')

    def _gerer_stabilisation(self, prochain_etat: EtatEvitement) -> None:
        """Maintient l'arrêt pendant la stabilisation de la tourelle."""
        self.arreter_moteurs()
        if monotonic() < self.fin_etape_s:
            return

        self.numero_distance_avant_mesure = self.numero_derniere_distance
        self.etat = prochain_etat

    def _nouvelle_distance_valide_disponible(self) -> bool:
        """Indique si une distance valide a été reçue depuis la stabilisation."""
        return (
            self.numero_derniere_distance > self.numero_distance_avant_mesure
            and self.derniere_distance_mm is not None
        )

    def _gerer_mesure_gauche(self) -> None:
        """Mémorise une nouvelle mesure gauche, puis oriente la tourelle au centre."""
        self.arreter_moteurs()
        if not self._nouvelle_distance_valide_disponible():
            return

        self.distance_gauche_mm = self.derniere_distance_mm
        self.publier_consigne_tourelle(self.angle_tourelle_centre_deg)
        self.fin_etape_s = monotonic() + self.delai_stabilisation_tourelle_s
        self.etat = EtatEvitement.STABILISATION_CENTRE

    def _gerer_mesure_centre(self) -> None:
        """Mémorise une nouvelle mesure centrale, puis oriente la tourelle à droite."""
        self.arreter_moteurs()
        if not self._nouvelle_distance_valide_disponible():
            return

        # La mesure centrale garantit que le balayage passe bien devant le robot.
        # Le choix de rotation reste volontairement fondé sur les mesures latérales.
        self.publier_consigne_tourelle(self.angle_tourelle_droite_deg)
        self.fin_etape_s = monotonic() + self.delai_stabilisation_tourelle_s
        self.etat = EtatEvitement.STABILISATION_DROITE

    def _gerer_mesure_droite(self) -> None:
        """Mémorise une nouvelle mesure droite et commence la rotation choisie."""
        self.arreter_moteurs()
        if not self._nouvelle_distance_valide_disponible():
            return

        distance_droite_mm = self.derniere_distance_mm
        distance_gauche_mm = self.distance_gauche_mm
        if distance_droite_mm is None or distance_gauche_mm is None:
            return

        self.distance_droite_mm = distance_droite_mm
        ecart_mm = distance_gauche_mm - distance_droite_mm
        if abs(ecart_mm) >= self.marge_choix_direction_mm:
            if ecart_mm > 0:
                self.dernier_cote_rotation = CoteRotation.GAUCHE
            else:
                self.dernier_cote_rotation = CoteRotation.DROITE

        if self.dernier_cote_rotation == CoteRotation.GAUCHE:
            vitesse = self.vitesse_rotation_recherche
            self.consigne_rotation = (-vitesse, vitesse)
        else:
            vitesse = self.vitesse_rotation_recherche
            self.consigne_rotation = (vitesse, -vitesse)

        self.publier_consigne_tourelle(self.angle_tourelle_centre_deg)
        self.fin_etape_s = monotonic() + self.delai_stabilisation_tourelle_s
        self.etat = EtatEvitement.STABILISATION_ROTATION
        if self.dernier_cote_rotation == CoteRotation.GAUCHE:
            self.publier_evenement('rotation_gauche')
        else:
            self.publier_evenement('rotation_droite')

    def _gerer_stabilisation_rotation(self) -> None:
        """Attend le recentrage de la tourelle avant de chercher un dégagement."""
        self.arreter_moteurs()
        if monotonic() < self.fin_etape_s:
            return

        self.nombre_mesures_degagement = 0
        self.debut_validation_degagement_s = (
            monotonic() + self.duree_rotation_recherche_min_s
        )
        self.fin_etape_s = monotonic() + self.duree_rotation_recherche_max_s
        self.etat = EtatEvitement.ROTATION

    def _gerer_rotation(self) -> None:
        """Tourne sur place jusqu'au dégagement ou jusqu'à l'expiration du délai."""
        if monotonic() >= self.fin_etape_s:
            self.arreter_moteurs()
            self.fin_etape_s = monotonic() + self.duree_recul_s
            self.etat = EtatEvitement.RECUL
            self.publier_evenement('recul_recuperation')
            return

        if self.derniere_distance_mm is None:
            self.arreter_moteurs()
            return

        self.publier_consigne_moteurs(*self.consigne_rotation)

    def _gerer_recul(self) -> None:
        """Recule brièvement après une recherche de dégagement infructueuse."""
        if monotonic() < self.fin_etape_s:
            self.publier_consigne_moteurs(-self.vitesse_recul, -self.vitesse_recul)
            return

        self.arreter_moteurs()
        self._commencer_analyse_obstacle()

    def _commencer_recentrage(self) -> None:
        """Arrête le robot et recentre la tourelle après un dégagement confirmé."""
        self.arreter_moteurs()
        self.publier_consigne_tourelle(self.angle_tourelle_centre_deg)
        self.fin_etape_s = monotonic() + self.delai_stabilisation_tourelle_s
        self.etat = EtatEvitement.RECENTRAGE

    def _gerer_recentrage(self) -> None:
        """Maintient l'arrêt pendant le recentrage de la tourelle."""
        self.arreter_moteurs()
        if monotonic() < self.fin_etape_s:
            return

        self.numero_distance_avant_mesure = self.numero_derniere_distance
        self.etat = EtatEvitement.VERIFICATION_REPRISE

    def _gerer_verification_reprise(self) -> None:
        """Attend une distance avant fraîche avant de reprendre ou réanalyser."""
        self.arreter_moteurs()
        if not self._nouvelle_distance_valide_disponible():
            return

        distance_avant_mm = self.derniere_distance_mm
        if distance_avant_mm is None:
            return

        if distance_avant_mm <= self.distance_arret_mm:
            self._commencer_analyse_obstacle()
            return

        self.etat = EtatEvitement.AVANCE
        self.publier_consigne_moteurs(self.vitesse_avance, self.vitesse_avance)
        self.publier_evenement('reprise_avance')

    def publier_evenement(self, evenement: str) -> None:
        """Publie un événement haut niveau lors d'une transition significative."""
        message = String()
        message.data = evenement
        self.evenement_robot_pub.publish(message)
        self.get_logger().info(f'Événement robot publié : {evenement}.')

    def publier_consigne_moteurs(self, gauche: int, droite: int) -> None:
        """Publie une consigne moteur bornée vers l'interface Pico."""
        message = ConsigneMoteurs()
        message.gauche = self._borner_consigne_moteur(gauche)
        message.droite = self._borner_consigne_moteur(droite)
        self.consigne_moteurs_pub.publish(message)

    def publier_consigne_tourelle(self, angle_deg: int) -> None:
        """Publie une consigne d'angle pour la tourelle."""
        message = Int32()
        message.data = angle_deg
        self.consigne_tourelle_pub.publish(message)

    def arreter_moteurs(self) -> None:
        """Publie une consigne d'arrêt explicite."""
        self.publier_consigne_moteurs(0, 0)


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2 et exécute le comportement d'évitement minimal."""
    # Garder le contexte actif assez longtemps pour publier l'arrêt moteur après Ctrl+C ou F5.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, _interrompre_execution)
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
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
