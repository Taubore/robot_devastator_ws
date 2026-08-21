# -*- coding: utf-8 -*-
"""
Nœud ROS 2 qui calcule l'odométrie du robot à partir des ticks encodeurs.
"""

from __future__ import annotations

import math
from time import monotonic
from typing import Final

import rclpy

from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_srvs.srv import Trigger
from tf2_ros import TransformBroadcaster

from commun.msg import EtatEncodeurs

TAILLE_FILE_MESSAGES: Final[int] = 10
TOPIC_ENCODEURS: Final[str] = '/pico/encodeurs'
TOPIC_ODOM: Final[str] = '/odom'
SERVICE_RESET: Final[str] = '/odometrie/reset'
FRAME_ODOM: Final[str] = 'odom'
FRAME_BASE: Final[str] = 'base_footprint'


class Odometrie(Node):
    """
    Cumule x, y, theta à partir des deltas de ticks gauche/droite et publie /odom et la TF.
    """

    def __init__(self) -> None:
        super().__init__('odometrie')

        # Ces paramètres sont mesurés en Phase 3 et chargés depuis
        # robot_devastator_bringup/config/mecanique.yaml au lancement. Les valeurs par
        # défaut ci-dessous ne servent qu'à un lancement isolé du nœud sans fichier YAML.
        self.declare_parameter('ticks_par_tour', 1447)
        self.declare_parameter('ticks_par_metre_gauche', 10492)
        self.declare_parameter('ticks_par_metre_droite', 10373)
        self.declare_parameter('ticks_par_metre_moyen', 10432)
        self.declare_parameter('entraxe_m', 0.200)

        self.ticks_par_tour = int(self.get_parameter('ticks_par_tour').value)
        self.ticks_par_metre_gauche = float(self.get_parameter('ticks_par_metre_gauche').value)
        self.ticks_par_metre_droite = float(self.get_parameter('ticks_par_metre_droite').value)
        self.ticks_par_metre_moyen = float(self.get_parameter('ticks_par_metre_moyen').value)
        self.entraxe_m = float(self.get_parameter('entraxe_m').value)

        if self.ticks_par_tour <= 0:
            raise ValueError("Le paramètre 'ticks_par_tour' doit être strictement positif.")
        if self.ticks_par_metre_gauche <= 0.0:
            raise ValueError(
                "Le paramètre 'ticks_par_metre_gauche' doit être strictement positif."
            )
        if self.ticks_par_metre_droite <= 0.0:
            raise ValueError(
                "Le paramètre 'ticks_par_metre_droite' doit être strictement positif."
            )
        if self.entraxe_m <= 0.0:
            raise ValueError("Le paramètre 'entraxe_m' doit être strictement positif.")

        # Pose cumulée depuis le démarrage du nœud ou le dernier appel à /odometrie/reset.
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        # None tant qu'aucun message n'a été reçu : sert à ignorer le premier delta,
        # qui n'a pas de référence, plutôt que d'intégrer un saut arbitraire.
        self.dernier_gauche_ticks: int | None = None
        self.dernier_droite_ticks: int | None = None
        self.dernier_instant_s: float | None = None

        self.publisher_odom = self.create_publisher(Odometry, TOPIC_ODOM, TAILLE_FILE_MESSAGES)
        self.diffuseur_tf = TransformBroadcaster(self)
        self.abonnement_encodeurs = self.create_subscription(
            EtatEncodeurs,
            TOPIC_ENCODEURS,
            self._recevoir_encodeurs_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.service_reset = self.create_service(
            Trigger,
            SERVICE_RESET,
            self._gerer_reset_callback,
        )

        self.get_logger().info(
            'Odométrie initialisée : '
            f'ticks_par_tour={self.ticks_par_tour}, '
            f'ticks_par_metre_gauche={self.ticks_par_metre_gauche}, '
            f'ticks_par_metre_droite={self.ticks_par_metre_droite}, '
            f'entraxe_m={self.entraxe_m}.'
        )

    # --- Callbacks des subscriptions ---

    def _recevoir_encodeurs_callback(self, message: EtatEncodeurs) -> None:
        """
        Intègre le delta de ticks depuis le message précédent et publie la pose à jour.
        """

        instant_s = monotonic()

        if self.dernier_gauche_ticks is None or self.dernier_droite_ticks is None:
            # Premier message reçu : aucune référence pour calculer un delta.
            # On mémorise seulement les ticks courants et on publie la pose initiale.
            self.dernier_gauche_ticks = message.gauche_ticks
            self.dernier_droite_ticks = message.droite_ticks
            self.dernier_instant_s = instant_s
            self._publier_odometrie(vitesse_lineaire_m_s=0.0, vitesse_angulaire_rad_s=0.0)
            return

        delta_gauche_ticks = message.gauche_ticks - self.dernier_gauche_ticks
        delta_droite_ticks = message.droite_ticks - self.dernier_droite_ticks
        dt_s = instant_s - self.dernier_instant_s if self.dernier_instant_s is not None else 0.0

        self.dernier_gauche_ticks = message.gauche_ticks
        self.dernier_droite_ticks = message.droite_ticks
        self.dernier_instant_s = instant_s

        self._mettre_a_jour_pose(delta_gauche_ticks, delta_droite_ticks, dt_s)

    # --- Callbacks des services ---

    def _gerer_reset_callback(
        self,
        _requete: object,
        reponse: Trigger.Response,
    ) -> Trigger.Response:
        """
        Remet x, y, theta à zéro sans toucher aux compteurs de ticks du Pico.
        """

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.get_logger().info('Odométrie remise à zéro (x=0, y=0, theta=0) sur demande.')
        reponse.success = True
        reponse.message = 'Odométrie remise à zéro (x=0, y=0, theta=0).'
        return reponse

    # --- Méthodes privées utilitaires ---

    def _mettre_a_jour_pose(
        self,
        delta_gauche_ticks: int,
        delta_droite_ticks: int,
        dt_s: float,
    ) -> None:
        """
        Applique la cinématique différentielle classique pour cumuler x, y, theta.
        """

        distance_gauche_m = delta_gauche_ticks / self.ticks_par_metre_gauche
        distance_droite_m = delta_droite_ticks / self.ticks_par_metre_droite
        distance_moyenne_m = (distance_gauche_m + distance_droite_m) / 2.0
        delta_theta_rad = (distance_droite_m - distance_gauche_m) / self.entraxe_m

        # Intégration par arc médian : on avance selon le cap moyen tenu pendant ce
        # petit déplacement (theta + la moitié de la rotation du cycle) plutôt que
        # selon le cap de départ. Plus fidèle à la trajectoire réelle qu'un Euler
        # simple dès qu'il y a une rotation notable entre deux messages encodeurs,
        # pour le même coût de calcul.
        cap_moyen_rad = self.theta + delta_theta_rad / 2.0
        self.x += distance_moyenne_m * math.cos(cap_moyen_rad)
        self.y += distance_moyenne_m * math.sin(cap_moyen_rad)

        # Normalisation dans [-pi, pi] via atan2(sin, cos) pour éviter une dérive
        # d'angle qui grandirait indéfiniment au fil des tours.
        theta_brut = self.theta + delta_theta_rad
        self.theta = math.atan2(math.sin(theta_brut), math.cos(theta_brut))

        vitesse_lineaire_m_s = distance_moyenne_m / dt_s if dt_s > 0.0 else 0.0
        vitesse_angulaire_rad_s = delta_theta_rad / dt_s if dt_s > 0.0 else 0.0

        self._publier_odometrie(vitesse_lineaire_m_s, vitesse_angulaire_rad_s)

    def _publier_odometrie(
        self,
        vitesse_lineaire_m_s: float,
        vitesse_angulaire_rad_s: float,
    ) -> None:
        """
        Publie le message Odometry courant et la transform odom -> base_footprint associée.
        """

        instant_ros = self.get_clock().now().to_msg()
        qz, qw = self._construire_quaternion_yaw(self.theta)

        message_odom = Odometry()
        message_odom.header.stamp = instant_ros
        message_odom.header.frame_id = FRAME_ODOM
        message_odom.child_frame_id = FRAME_BASE
        message_odom.pose.pose.position.x = self.x
        message_odom.pose.pose.position.y = self.y
        message_odom.pose.pose.orientation.z = qz
        message_odom.pose.pose.orientation.w = qw
        message_odom.twist.twist.linear.x = vitesse_lineaire_m_s
        message_odom.twist.twist.angular.z = vitesse_angulaire_rad_s
        self.publisher_odom.publish(message_odom)

        transform = TransformStamped()
        transform.header.stamp = instant_ros
        transform.header.frame_id = FRAME_ODOM
        transform.child_frame_id = FRAME_BASE
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw
        self.diffuseur_tf.sendTransform(transform)

    def _construire_quaternion_yaw(self, theta: float) -> tuple[float, float]:
        """
        Convertit un angle de cap en quaternion (qz, qw) : robot 2D, sans roulis ni tangage.
        """

        return math.sin(theta / 2.0), math.cos(theta / 2.0)


def main(args: list[str] | None = None) -> None:
    """
    Initialise ROS 2 puis exécute le nœud jusqu'à son arrêt.
    """

    rclpy.init(args=args)
    noeud: Odometrie | None = None

    try:
        noeud = Odometrie()
        rclpy.spin(noeud)
    except KeyboardInterrupt:
        pass
    finally:
        if noeud is not None:
            noeud.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
