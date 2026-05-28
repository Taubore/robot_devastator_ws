# -*- coding: utf-8 -*-
"""Nœud ROS 2 simple qui relie les interfaces ROS au transport série du Pico."""

from __future__ import annotations

from collections import deque
from typing import Final, Protocol, cast

import rclpy
import serial
from commun.msg import ConsigneMoteurs
from rclpy.node import Node
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
MODE_MATERIEL_REEL: Final[str] = 'reel'
MODE_MATERIEL_SIMULATION: Final[str] = 'simulation'
MODES_MATERIEL_VALIDES: Final[set[str]] = {
    MODE_MATERIEL_REEL,
    MODE_MATERIEL_SIMULATION,
}


class TransportPico(Protocol):
    """Méthodes communes attendues par le nœud, peu importe le mode matériel."""

    def connecter(self) -> None:
        """Prépare le transport si nécessaire."""

    def fermer(self) -> None:
        """Libère les ressources du transport."""

    def lire_ligne(self) -> str | None:
        """Retourne une ligne d'état disponible, sinon `None`."""

    def ping(self) -> None:
        """Teste la liaison logique avec le Pico."""

    def stop(self) -> None:
        """Demande l'arrêt immédiat des moteurs."""

    def demander_distance(self) -> None:
        """Demande une mesure de distance ultrason au Pico."""

    def set_servo(self, angle: int) -> None:
        """Envoie une consigne d'angle au servo de tourelle."""

    def set_moteurs(self, gauche: int, droite: int) -> None:
        """Envoie une consigne moteur brute gauche/droite."""


class MessageConsigneMoteurs(Protocol):
    """Champs attendus du message ROS `commun/msg/ConsigneMoteurs`."""

    gauche: int
    droite: int


class ReponseTrigger(Protocol):
    """Champs modifiés dans une réponse ROS `std_srvs/srv/Trigger`."""

    success: bool
    message: str


class MessageTexte(Protocol):
    """Champ attendu du message ROS `std_msgs/msg/String`."""

    data: str


class MessageEntier(Protocol):
    """Champ attendu du message ROS `std_msgs/msg/Int32`."""

    data: int


class TransportSimulationPico:
    """Transport minimal qui imite les réponses du Pico sans ouvrir d'UART."""

    def __init__(self) -> None:
        self._lignes_etat: deque[str] = deque(["SIMULATION OK"])
        self._derniere_consigne: tuple[int, int] | None = None
        self._distance_simulee_mm = 500

    def connecter(self) -> None:
        """Prépare le transport simulé."""

    def fermer(self) -> None:
        """Ferme le transport simulé."""

    def lire_ligne(self) -> str | None:
        """Retourne la prochaine ligne d'état simulée."""
        if not self._lignes_etat:
            return None
        return self._lignes_etat.popleft()

    def ping(self) -> None:
        """Simule une commande `PING` réussie."""
        self._lignes_etat.append("SIMULATION PING OK")

    def stop(self) -> None:
        """Simule une commande `STOP` réussie."""
        self._lignes_etat.append("SIMULATION STOP")

    def demander_distance(self) -> None:
        """Simule une réponse numérique à la commande `DIST`."""
        self._lignes_etat.append(str(self._distance_simulee_mm))

    def set_servo(self, angle: int) -> None:
        """Simule l'envoi d'une consigne d'angle au servo de tourelle."""
        if not ANGLE_SERVO_MIN <= angle <= ANGLE_SERVO_MAX:
            raise ValueError("angle hors plage 0..180")

        self._lignes_etat.append(f"SIMULATION SERVO angle={angle}")

    def set_moteurs(self, gauche: int, droite: int) -> None:
        """Simule l'envoi d'une consigne moteur brute gauche/droite."""
        if not VALEUR_MOTEUR_MIN <= gauche <= VALEUR_MOTEUR_MAX:
            raise ValueError("gauche hors plage -1000..1000")
        if not VALEUR_MOTEUR_MIN <= droite <= VALEUR_MOTEUR_MAX:
            raise ValueError("droite hors plage -1000..1000")

        consigne = (gauche, droite)
        if consigne == self._derniere_consigne:
            return

        self._derniere_consigne = consigne
        self._lignes_etat.append(f"SIMULATION SET gauche={gauche} droite={droite}")


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
        self.declare_parameter('periode_distance_s', 0.5)
        self.declare_parameter('mode_materiel', MODE_MATERIEL_REEL)

        self.port = str(self.get_parameter('port').value)
        self.debit = int(self.get_parameter('debit').value)
        timeout_lecture = float(self.get_parameter('timeout_lecture').value)
        periode_maintien_s = float(self.get_parameter('periode_maintien_s').value)
        periode_distance_s = float(self.get_parameter('periode_distance_s').value)
        self.mode_materiel = str(self.get_parameter('mode_materiel').value)

        if timeout_lecture <= 0.0:
            raise ValueError("Le paramètre 'timeout_lecture' doit être strictement positif.")
        if periode_maintien_s <= 0.0:
            raise ValueError("Le paramètre 'periode_maintien_s' doit être strictement positif.")
        if periode_distance_s <= 0.0:
            raise ValueError("Le paramètre 'periode_distance_s' doit être strictement positif.")
        if self.mode_materiel not in MODES_MATERIEL_VALIDES:
            raise ValueError(
                "Le paramètre 'mode_materiel' doit valoir "
                f"'{MODE_MATERIEL_REEL}' ou '{MODE_MATERIEL_SIMULATION}'."
            )

        if self.mode_materiel == MODE_MATERIEL_REEL:
            self.transport: TransportPico = TransportSeriePico(
                ConfigurationUART(
                    port=self.port,
                    debit=self.debit,
                    timeout_lecture=timeout_lecture,
                )
            )
        else:
            self.transport = TransportSimulationPico()

        self._uart_disponible = False

        self.derniere_consigne: tuple[int, int] | None = None

        self.publisher_etat = self.create_publisher(
            String,
            'etat_pico',
            TAILLE_FILE_MESSAGES,
        )
        self.publisher_distance = self.create_publisher(
            Int32,
            'distance_ultrason_mm',
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_consigne = self.create_subscription(
            ConsigneMoteurs,
            'consigne_moteurs',
            self._recevoir_consigne_moteurs,
            TAILLE_FILE_MESSAGES,
        )
        self.abonnement_tourelle = self.create_subscription(
            Int32,
            'commande_tourelle_deg',
            self._recevoir_commande_tourelle,
            TAILLE_FILE_MESSAGES,
        )
        self.service_stop = self.create_service(Trigger, 'stop', self._gerer_stop)
        self.service_ping = self.create_service(Trigger, 'ping', self._gerer_ping)

        # Un timer pour relire le port sans boucle bloquante, un autre pour
        # renvoyer la consigne mémorisée avant le timeout de 500 ms du Pico.
        self.timer_lecture = self.create_timer(timeout_lecture, self._lire_et_publier_etat)
        self.timer_maintien = self.create_timer(
            periode_maintien_s,
            self._maintenir_derniere_consigne,
        )
        self.timer_distance = self.create_timer(
            periode_distance_s,
            self._demander_distance,
        )

        if periode_maintien_s >= 0.5:
            self.get_logger().warn(
                "La période de maintien est supérieure ou égale à 0,5 s, "
                "le Pico risque donc de couper les moteurs."
            )

        self._verifier_liaison_serie()

    def _demander_distance(self) -> None:
        """Demande périodiquement une mesure de distance au Pico."""
        if not self._verifier_liaison_serie():
            return

        try:
            self.transport.demander_distance()
        except (serial.SerialException, OSError) as erreur:
            self.get_logger().error(f"Demande de distance impossible: {erreur}")
            self.transport.fermer()
            self._uart_disponible = False

    def _recevoir_commande_tourelle(self, message: Int32) -> None:
        """Valide puis envoie une consigne d'angle pour le servo de tourelle."""
        message_entier = cast(MessageEntier, message)
        angle = int(message_entier.data)

        if not ANGLE_SERVO_MIN <= angle <= ANGLE_SERVO_MAX:
            self.get_logger().warn(
                f"Commande tourelle ignorée car hors plage : {angle}"
            )
            return
        if not self._verifier_liaison_serie():
            return

        try:
            self.transport.set_servo(angle)
        except (serial.SerialException, OSError) as erreur:
            self.get_logger().error(f"Commande tourelle impossible: {erreur}")
            self.transport.fermer()
            self._uart_disponible = False

    def _verifier_liaison_serie(self) -> bool:
        """Essaie d'ouvrir la liaison Pico et journalise les transitions d'état."""
        try:
            self.transport.connecter()
        except (serial.SerialException, OSError) as erreur:
            if self._uart_disponible:
                self.get_logger().error(f"Liaison UART perdue: {erreur}")
            else:
                self.get_logger().warn(
                    f"Liaison UART indisponible au démarrage ou en reprise: {erreur}"
                )
            self._uart_disponible = False
            return False

        if not self._uart_disponible:
            if self.mode_materiel == MODE_MATERIEL_REEL:
                self.get_logger().info(
                    "Interface Pico ouverte sur "
                    f"{self.port} à {self.debit} bauds."
                )
            else:
                self.get_logger().info("Interface Pico en mode simulation.")
        self._uart_disponible = True
        return True

    def _recevoir_consigne_moteurs(self, message: ConsigneMoteurs) -> None:
        """Valide puis envoie immédiatement une consigne moteur."""
        consigne = cast(MessageConsigneMoteurs, message)
        gauche = int(consigne.gauche)
        droite = int(consigne.droite)

        if not VALEUR_MOTEUR_MIN <= gauche <= VALEUR_MOTEUR_MAX:
            self.get_logger().warn(
                f"Consigne gauche ignorée car hors plage : {gauche}"
            )
            return
        if not VALEUR_MOTEUR_MIN <= droite <= VALEUR_MOTEUR_MAX:
            self.get_logger().warn(
                f"Consigne droite ignorée car hors plage : {droite}"
            )
            return
        if not self._verifier_liaison_serie():
            return

        try:
            self.transport.set_moteurs(gauche, droite)
        except (serial.SerialException, OSError) as erreur:
            self.get_logger().error(f"Envoi UART impossible: {erreur}")
            self.transport.fermer()
            self._uart_disponible = False
            return

        self.derniere_consigne = (gauche, droite)

    def _maintenir_derniere_consigne(self) -> None:
        """Répète la dernière consigne valide pour éviter le timeout du Pico."""
        if self.derniere_consigne is None:
            return
        if not self._verifier_liaison_serie():
            return

        gauche, droite = self.derniere_consigne
        try:
            self.transport.set_moteurs(gauche, droite)
        except (serial.SerialException, OSError) as erreur:
            self.get_logger().error(f"Maintien de consigne impossible: {erreur}")
            self.transport.fermer()
            self._uart_disponible = False

    def _lire_et_publier_etat(self) -> None:
        """Publie en ROS 2 toute ligne texte éventuellement renvoyée par le Pico."""
        if not self._verifier_liaison_serie():
            return
        try:
            ligne = self.transport.lire_ligne()
        except (serial.SerialException, OSError) as erreur:
            self.get_logger().error(f"Lecture UART impossible: {erreur}")
            self.transport.fermer()
            self._uart_disponible = False
            return

        if not ligne:
            return

        self.get_logger().info(f"État Pico : {ligne}")

        message = String()
        message_texte = cast(MessageTexte, message)
        message_texte.data = ligne
        self.publisher_etat.publish(message)

        if ligne.isdecimal():
            message_distance = Int32()
            message_entier = cast(MessageEntier, message_distance)
            message_entier.data = int(ligne)
            self.publisher_distance.publish(message_distance)

    def _gerer_stop(self, _requete: object, reponse: ReponseTrigger) -> ReponseTrigger:
        """Demande l'arrêt moteur et mémorise une consigne nulle."""
        try:
            self.transport.stop()
        except (serial.SerialException, OSError) as erreur:
            self.transport.fermer()
            self._uart_disponible = False
            reponse.success = False
            reponse.message = f"STOP non envoyé : {erreur}"
            return reponse

        self.derniere_consigne = (0, 0)
        reponse.success = True
        reponse.message = "Commande STOP acceptée."
        return reponse

    def _gerer_ping(self, _requete: object, reponse: ReponseTrigger) -> ReponseTrigger:
        """Traite simplement `PING`."""
        try:
            self.transport.ping()
        except (serial.SerialException, OSError) as erreur:
            self.transport.fermer()
            self._uart_disponible = False
            reponse.success = False
            reponse.message = f"PING non envoyé : {erreur}"
            return reponse

        reponse.success = True
        reponse.message = "Commande PING acceptée."
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
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
