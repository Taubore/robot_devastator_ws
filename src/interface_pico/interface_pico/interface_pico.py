# -*- coding: utf-8 -*-
"""
Nœud ROS 2 qui relie les interfaces ROS au transport série (UART) du Pico.
"""

from __future__ import annotations

import rclpy
import serial

from rclpy.node import Node

from typing import Final

from commun.msg import ConsigneMoteurs
from std_msgs.msg import Int32, String
from std_srvs.srv import Trigger

from .transport_serie_pico import (
    ANGLE_SERVO_MAX,
    ANGLE_SERVO_MIN,
    ConfigurationUART,
    TransportSeriePico,
    VALEUR_MOTEUR_MAX,
    VALEUR_MOTEUR_MIN,
)

TAILLE_FILE_MESSAGES: Final[int] = 10
TOPIC_COMMANDE_MOTEURS: Final[str] = '/pico/commande_moteurs'
TOPIC_COMMANDE_TOURELLE: Final[str] = '/pico/commande_tourelle_deg'
TOPIC_DISTANCE_ULTRASON: Final[str] = '/pico/distance_ultrason_mm'
TOPIC_ETAT_PICO: Final[str] = '/pico/etat'
SERVICE_PING: Final[str] = '/pico/ping'
SERVICE_STOP: Final[str] = '/pico/stop'


class NoeudInterfacePico(Node):
    """
    Adapte ROS 2 vers la liaison UART du Pico sans logique complexe.
    """

    def __init__(self) -> None:
        super().__init__('interface_pico_node')

        # Ces paramètres couvrent l'essentiel du câblage série et du maintien
        # périodique demandé par le Pico.
        self.declare_parameter('port', '/dev/ttyS0')
        self.declare_parameter('debit', 115200)
        self.declare_parameter('timeout_lecture', 0.1)
        self.declare_parameter('periode_maintien_s', 0.1)
        self.declare_parameter('periode_distance_s', 0.5)

        self.port = str(self.get_parameter('port').value)
        self.debit = int(self.get_parameter('debit').value)
        timeout_lecture = float(self.get_parameter('timeout_lecture').value)
        periode_maintien_s = float(self.get_parameter('periode_maintien_s').value)
        periode_distance_s = float(self.get_parameter('periode_distance_s').value)

        if timeout_lecture <= 0.0:
            raise ValueError("Le paramètre 'timeout_lecture' doit être strictement positif.")
        if periode_maintien_s <= 0.0:
            raise ValueError("Le paramètre 'periode_maintien_s' doit être strictement positif.")
        if periode_distance_s <= 0.0:
            raise ValueError("Le paramètre 'periode_distance_s' doit être strictement positif.")
        self.transport = TransportSeriePico(
            ConfigurationUART(
                port=self.port,
                debit=self.debit,
                timeout_lecture=timeout_lecture,
            )
        )

        self._uart_disponible = False
        self._indisponibilite_uart_journalisee = False

        self.derniere_consigne_moteurs: tuple[int, int] | None = None

        self.publisher_etat = self.create_publisher(
            String,
            TOPIC_ETAT_PICO,
            TAILLE_FILE_MESSAGES,
        )
        self.publisher_distance = self.create_publisher(
            Int32,
            TOPIC_DISTANCE_ULTRASON,
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_consigne_moteurs = self.create_subscription(
            ConsigneMoteurs,
            TOPIC_COMMANDE_MOTEURS,
            self._recevoir_consigne_moteurs_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_tourelle = self.create_subscription(
            Int32,
            TOPIC_COMMANDE_TOURELLE,
            self._recevoir_commande_tourelle_callback,
            TAILLE_FILE_MESSAGES,
        )
        self.service_stop = self.create_service(Trigger, SERVICE_STOP, self._gerer_stop_callback)
        self.service_ping = self.create_service(Trigger, SERVICE_PING, self._gerer_ping_callback)

        # Un timer relit le port sans boucle bloquante, un autre renvoie la consigne
        # des moteurs mémorisée avant le timeout de 500 ms du Pico et le dernier demande
        # la distance.
        self.timer_lecture = self.create_timer(
            timeout_lecture,
            self._lire_et_traiter_reponse_uart_callback
        )
        self.timer_maintien_consigne_moteurs = self.create_timer(
            periode_maintien_s,
            self._maintenir_derniere_consigne_moteurs_callback,
        )
        self.timer_distance = self.create_timer(
            periode_distance_s,
            self._demander_distance_callback,
        )

        if periode_maintien_s >= 0.5:
            self.get_logger().warn(
                'La période de maintien est supérieure ou égale à 0,5 s, '
                'le Pico risque donc de couper les moteurs.'
            )

        self._verifier_liaison_serie()

    # --- Callbacks des subscriptions ---

    def _recevoir_commande_tourelle_callback(self, message: Int32) -> None:
        """
        Envoie une consigne d'angle valide au servo de tourelle.
        """

        angle = int(message.data)

        if not ANGLE_SERVO_MIN <= angle <= ANGLE_SERVO_MAX:
            self.get_logger().warn(
                f'Commande tourelle ignorée car hors plage : {angle}'
            )
            return
        if not self._verifier_liaison_serie():
            return

        try:
            self.transport.set_servo(angle)
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Commande tourelle impossible: {erreur}')

    def _recevoir_consigne_moteurs_callback(self, message: ConsigneMoteurs) -> None:
        """
        Envoie immédiatement une consigne moteur valide.
        """

        gauche = int(message.gauche)
        droite = int(message.droite)

        if not VALEUR_MOTEUR_MIN <= gauche <= VALEUR_MOTEUR_MAX:
            self.get_logger().warn(
                f'Consigne du moteur gauche ignorée car hors plage : {gauche}'
            )
            return
        if not VALEUR_MOTEUR_MIN <= droite <= VALEUR_MOTEUR_MAX:
            self.get_logger().warn(
                f'Consigne du moteur droit ignorée car hors plage : {droite}'
            )
            return
        if not self._verifier_liaison_serie():
            return

        try:
            self.transport.set_moteurs(gauche, droite)
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Envoi UART impossible: {erreur}')
            return

        self.derniere_consigne_moteurs = (gauche, droite)

    # --- Callbacks des services ---

    def _gerer_stop_callback(self, _requete: object, reponse: Trigger.Response) -> Trigger.Response:
        """
        Demande l'arrêt moteur et mémorise une consigne des moteurs nulle.
        """

        try:
            self.transport.stop()
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Commande STOP impossible: {erreur}')
            reponse.success = False
            reponse.message = f'STOP non envoyé : {erreur}'
            return reponse

        self.derniere_consigne_moteurs = (0, 0)
        reponse.success = True
        reponse.message = 'Commande STOP acceptée.'
        return reponse

    def _gerer_ping_callback(self, _requete: object, reponse: Trigger.Response) -> Trigger.Response:
        """
        Traite simplement `PING`.
        """

        try:
            self.transport.ping()
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Commande PING impossible: {erreur}')
            reponse.success = False
            reponse.message = f'PING non envoyé : {erreur}'
            return reponse

        reponse.success = True
        reponse.message = 'Commande PING acceptée.'
        return reponse

    # --- Callbacks des timers ---

    def _demander_distance_callback(self) -> None:
        """
        Demande périodiquement une mesure de distance au Pico.
        """

        if not self._verifier_liaison_serie():
            return

        try:
            self.transport.demander_distance()
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Demande de distance impossible: {erreur}')

    def _maintenir_derniere_consigne_moteurs_callback(self) -> None:
        """
        Répète la dernière consigne des moteurs valide pour éviter le timeout du Pico.
        """

        if self.derniere_consigne_moteurs is None:
            return
        if not self._verifier_liaison_serie():
            return

        gauche, droite = self.derniere_consigne_moteurs
        try:
            self.transport.set_moteurs(gauche, droite)
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Maintien de consigne des moteurs impossible: {erreur}')

    def _lire_et_traiter_reponse_uart_callback(self) -> None:
        """
        Publie en ROS 2 toute ligne texte éventuellement renvoyée par le Pico.
        """

        if not self._verifier_liaison_serie():
            return
        try:
            ligne = self.transport.lire_ligne()
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Lecture UART impossible: {erreur}')
            return

        if not ligne:
            return

        message = String()
        message.data = ligne
        self.publisher_etat.publish(message)

        # Une valeur numérique représente une distance. Les autres lignes sont
        # des messages texte du Pico à journaliser selon leur gravité.
        if ligne.isdecimal():
            message_distance = Int32()
            message_distance.data = int(ligne)
            self.publisher_distance.publish(message_distance)
        elif ligne.startswith('ERREUR'):
            self.get_logger().error(f'Réponse UART du Pico : {ligne}')
        elif ligne.startswith('WARN'):
            self.get_logger().warn(f'Réponse UART du Pico : {ligne}')
        else:
            self.get_logger().debug(f'Réponse UART du Pico : {ligne}')

    # --- Méthodes privées utilitaires ---

    def _signaler_erreur_uart(self, message: str) -> None:
        """
        Ferme le port après une erreur UART déjà expliquée dans les logs.
        """

        self.get_logger().error(message)
        self.transport.fermer()
        self._uart_disponible = False
        self._indisponibilite_uart_journalisee = True

    def _verifier_liaison_serie(self) -> bool:
        """
        Essaie d'ouvrir la liaison Pico et journalise les transitions d'état.
        """

        try:
            self.transport.connecter()
        except (serial.SerialException, OSError) as erreur:
            if self._uart_disponible:
                self.get_logger().error(f'Liaison UART perdue: {erreur}')
            elif not self._indisponibilite_uart_journalisee:
                self.get_logger().warn(
                    f'Liaison UART indisponible au démarrage ou en reprise: {erreur}'
                )
            self._uart_disponible = False
            self._indisponibilite_uart_journalisee = True
            return False

        if not self._uart_disponible:
            self.get_logger().info(
                f'Interface Pico ouverte sur {self.port} à {self.debit} bauds.'
            )
        self._uart_disponible = True
        self._indisponibilite_uart_journalisee = False
        return True

    # --- Cycle de vie du nœud ---

    def destroy_node(self) -> bool:
        """
        Ferme le port série avant l'arrêt complet du nœud.
        """

        self.transport.fermer()
        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """
    Initialise ROS 2 puis exécute le nœud jusqu'à son arrêt.
    """

    rclpy.init(args=args)
    noeud: NoeudInterfacePico | None = None

    try:
        noeud = NoeudInterfacePico()
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
