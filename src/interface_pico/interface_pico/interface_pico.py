# -*- coding: utf-8 -*-
"""Nœud ROS 2 simple qui relie les interfaces ROS au transport série du Pico."""

from __future__ import annotations

from typing import Final

import rclpy
import serial
from commun.msg import ConsigneMoteurs
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger

from .transport_serie_pico import (
    ConfigurationUART,
    TransportSeriePico,
    VALEUR_MOTEUR_MAX,
    VALEUR_MOTEUR_MIN,
)

TAILLE_FILE_MESSAGES: Final[int] = 10


class NoeudInterfacePico(Node):
    """Adapte ROS 2 vers la liaison UART du Pico sans logique complexe."""

    def __init__(self) -> None:
        super().__init__('interface_pico_node')

        # Ces paramètres couvrent l'essentiel du câblage série et du maintien
        # périodique demandé par le Pico.
        self.declare_parameter('port', '/dev/ttyS0')
        self.declare_parameter('debit', 115200)
        self.declare_parameter('timeout_lecture', 0.1)
        self.declare_parameter('periode_maintien_s', 0.1)

        port = str(self.get_parameter('port').value)
        debit = int(self.get_parameter('debit').value)
        timeout_lecture = float(self.get_parameter('timeout_lecture').value)
        periode_maintien_s = float(self.get_parameter('periode_maintien_s').value)

        if timeout_lecture <= 0.0:
            raise ValueError("Le paramètre 'timeout_lecture' doit être strictement positif.")
        if periode_maintien_s <= 0.0:
            raise ValueError("Le paramètre 'periode_maintien_s' doit être strictement positif.")

        self.transport = TransportSeriePico(
            ConfigurationUART(
                port=port,
                debit=debit,
                timeout_lecture=timeout_lecture,
            )
        )
        self._uart_disponible = False

        self.derniere_consigne: tuple[int, int] | None = None

        self.publisher_etat = self.create_publisher(
            String,
            'etat_pico',
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_consigne = self.create_subscription(
            ConsigneMoteurs,
            'consigne_moteurs',
            self._recevoir_consigne_moteurs,
            TAILLE_FILE_MESSAGES,
        )
        self.service_stop = self.create_service(Trigger, 'stop', self._gerer_stop)
        self.service_ping = self.create_service(Trigger, 'ping', self._gerer_ping)

        # Un timer pour relire le port sans boucle bloquante, un autre pour
        # renvoyer la consigne mémorisée avant le timeout de 500 ms du Pico.
        self.timer_lecture = self.create_timer(timeout_lecture, self._lire_et_publier_etat)
        self.timer_maintien = self.create_timer(periode_maintien_s, self._maintenir_derniere_consigne)

        if periode_maintien_s >= 0.5:
            self.get_logger().warn(
                "La période de maintien est supérieure ou égale à 0,5 s, "
                "le Pico risque donc de couper les moteurs."
            )

        self._verifier_liaison_serie()

    def _verifier_liaison_serie(self) -> bool:
        """Essaie d'ouvrir la liaison série et journalise les transitions d'état."""
        try:
            self.transport.connecter()
        except (serial.SerialException, OSError) as erreur:  # pragma: no cover - dépend du matériel série.
            if self._uart_disponible:
                self.get_logger().error(f"Liaison UART perdue: {erreur}")
            else:
                self.get_logger().warn(
                    f"Liaison UART indisponible au démarrage ou en reprise: {erreur}"
                )
            self._uart_disponible = False
            return False

        if not self._uart_disponible:
            self.get_logger().info(
                "Interface Pico ouverte sur "
                f"{self.transport.configuration.port} à "
                f"{self.transport.configuration.debit} bauds."
            )
        self._uart_disponible = True
        return True

    def _recevoir_consigne_moteurs(self, message: ConsigneMoteurs) -> None:
        """Valide puis envoie immédiatement une consigne moteur."""
        if not VALEUR_MOTEUR_MIN <= message.gauche <= VALEUR_MOTEUR_MAX:
            self.get_logger().warn(
                f"Consigne gauche ignorée car hors plage : {message.gauche}"
            )
            return
        if not VALEUR_MOTEUR_MIN <= message.droite <= VALEUR_MOTEUR_MAX:
            self.get_logger().warn(
                f"Consigne droite ignorée car hors plage : {message.droite}"
            )
            return
        if not self._verifier_liaison_serie():
            return

        try:
            self.transport.set_moteurs(message.gauche, message.droite)
        except (serial.SerialException, OSError) as erreur:  # pragma: no cover - dépend du matériel série.
            self.get_logger().error(f"Envoi UART impossible: {erreur}")
            self.transport.fermer()
            self._uart_disponible = False
            return

        self.derniere_consigne = (message.gauche, message.droite)

    def _maintenir_derniere_consigne(self) -> None:
        """Répète la dernière consigne valide pour éviter le timeout du Pico."""
        if self.derniere_consigne is None:
            return
        if not self._verifier_liaison_serie():
            return

        gauche, droite = self.derniere_consigne
        try:
            self.transport.set_moteurs(gauche, droite)
        except (serial.SerialException, OSError) as erreur:  # pragma: no cover - dépend du matériel série.
            self.get_logger().error(f"Maintien de consigne impossible: {erreur}")
            self.transport.fermer()
            self._uart_disponible = False

    def _lire_et_publier_etat(self) -> None:
        """Publie en ROS 2 toute ligne texte éventuellement renvoyée par le Pico."""
        if not self._verifier_liaison_serie():
            return
        try:
            ligne = self.transport.lire_ligne()
        except (serial.SerialException, OSError) as erreur:  # pragma: no cover - dépend du matériel série.
            self.get_logger().error(f"Lecture UART impossible: {erreur}")
            self.transport.fermer()
            self._uart_disponible = False
            return

        if not ligne:
            return

        message = String()
        message.data = ligne
        self.publisher_etat.publish(message)

    def _gerer_stop(self, _requete: Trigger.Request, reponse: Trigger.Response) -> Trigger.Response:
        """Arrête le Pico et mémorise une consigne nulle."""
        try:
            self.transport.stop()
        except (serial.SerialException, OSError) as erreur:  # pragma: no cover - dépend du matériel série.
            self.transport.fermer()
            self._uart_disponible = False
            reponse.success = False
            reponse.message = f"STOP non envoyé : {erreur}"
            return reponse

        self.derniere_consigne = (0, 0)
        reponse.success = True
        reponse.message = "Commande STOP envoyée au Pico."
        return reponse

    def _gerer_ping(self, _requete: Trigger.Request, reponse: Trigger.Response) -> Trigger.Response:
        """Envoie simplement `PING` au Pico."""
        try:
            self.transport.ping()
        except (serial.SerialException, OSError) as erreur:  # pragma: no cover - dépend du matériel série.
            self.transport.fermer()
            self._uart_disponible = False
            reponse.success = False
            reponse.message = f"PING non envoyé : {erreur}"
            return reponse

        reponse.success = True
        reponse.message = "Commande PING envoyée au Pico."
        return reponse

    def destroy_node(self) -> bool:
        """Ferme le port série avant l'arrêt complet du nœud."""
        self.transport.fermer()
        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2 puis exécute le nœud jusqu'à son arrêt."""
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
        rclpy.shutdown()

if __name__ == '__main__':
    main()