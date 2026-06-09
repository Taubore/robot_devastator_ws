# -*- coding: utf-8 -*-
"""
Nœud ROS 2 qui relie les interfaces ROS au transport série (UART) du Pico.
"""

from __future__ import annotations

from time import monotonic
from typing import Final

import rclpy
import serial

from rclpy.node import Node

from commun.msg import ConsigneMoteurs, EtatEncodeurs
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
TOPIC_ENCODEURS: Final[str] = '/pico/encodeurs'
TOPIC_ETAT_PICO: Final[str] = '/pico/etat'
SERVICE_PING: Final[str] = '/pico/ping'
SERVICE_STOP_MOTEURS: Final[str] = '/pico/stop_moteurs'
SERVICE_RESET_ENCODEURS: Final[str] = '/pico/reset_encodeurs'


class InterfacePico(Node):
    """
    Traduit les commandes ROS 2 vers UART et publie les états Pico.
    """

    def __init__(self) -> None:
        super().__init__('interface_pico')

        # Ces paramètres couvrent l'essentiel du câblage série, du maintien
        # périodique demandé par le Pico et des lectures simples de capteurs.
        self.declare_parameter('port', '/dev/ttyS0')
        self.declare_parameter('debit', 115200)
        self.declare_parameter('timeout_lecture', 0.1)
        self.declare_parameter('periode_maintien_s', 0.1)
        self.declare_parameter('delai_expiration_consigne_moteurs_s', 0.5)
        self.declare_parameter('periode_distance_s', 0.5)
        self.declare_parameter('periode_encodeurs_s', 0.1)
        self.declare_parameter('delai_attente_reponse_service_s', 1.0)

        self.port = str(self.get_parameter('port').value)
        self.debit = int(self.get_parameter('debit').value)
        timeout_lecture = float(self.get_parameter('timeout_lecture').value)
        periode_maintien_s = float(self.get_parameter('periode_maintien_s').value)
        self.delai_expiration_consigne_moteurs_s = float(
            self.get_parameter('delai_expiration_consigne_moteurs_s').value
        )
        periode_distance_s = float(self.get_parameter('periode_distance_s').value)
        periode_encodeurs_s = float(self.get_parameter('periode_encodeurs_s').value)
        self.delai_attente_reponse_service_s = float(
            self.get_parameter('delai_attente_reponse_service_s').value
        )

        if timeout_lecture <= 0.0:
            raise ValueError("Le paramètre 'timeout_lecture' doit être strictement positif.")
        if periode_maintien_s <= 0.0:
            raise ValueError("Le paramètre 'periode_maintien_s' doit être strictement positif.")
        if self.delai_expiration_consigne_moteurs_s <= 0.0:
            raise ValueError(
                "Le paramètre 'delai_expiration_consigne_moteurs_s' "
                'doit être strictement positif.'
            )
        if periode_distance_s <= 0.0:
            raise ValueError("Le paramètre 'periode_distance_s' doit être strictement positif.")
        if periode_encodeurs_s <= 0.0:
            raise ValueError("Le paramètre 'periode_encodeurs_s' doit être strictement positif.")
        if self.delai_attente_reponse_service_s <= 0.0:
            raise ValueError(
                "Le paramètre 'delai_attente_reponse_service_s' doit être strictement positif."
            )

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
        self.instant_derniere_consigne_moteurs_s: float | None = None

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
        self.publisher_encodeurs = self.create_publisher(
            EtatEncodeurs,
            TOPIC_ENCODEURS,
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
        self.service_stop_moteurs = self.create_service(
            Trigger,
            SERVICE_STOP_MOTEURS,
            self._gerer_stop_moteurs_callback,
        )
        self.service_ping = self.create_service(Trigger, SERVICE_PING, self._gerer_ping_callback)
        self.service_reset_encodeurs = self.create_service(
            Trigger,
            SERVICE_RESET_ENCODEURS,
            self._gerer_reset_encodeurs_callback,
        )

        # Un timer relit le port sans boucle bloquante, un autre renvoie temporairement
        # la consigne mémorisée avant le timeout de 500 ms du Pico. Deux timers demandent
        # les mesures sonar et encodeurs. Une commande ROS trop ancienne force un arrêt.
        self.timer_lecture = self.create_timer(
            timeout_lecture,
            self._lire_et_traiter_reponse_uart_callback,
        )
        self.timer_maintien_consigne_moteurs = self.create_timer(
            periode_maintien_s,
            self._maintenir_derniere_consigne_moteurs_callback,
        )
        self.timer_distance = self.create_timer(
            periode_distance_s,
            self._demander_distance_callback,
        )
        self.timer_encodeurs = self.create_timer(
            periode_encodeurs_s,
            self._demander_encodeurs_callback,
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
            self._signaler_erreur_uart(f'Commande tourelle impossible : {erreur}')

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
            self._signaler_erreur_uart(f'Envoi UART impossible : {erreur}')
            return

        self.derniere_consigne_moteurs = (gauche, droite)
        self.instant_derniere_consigne_moteurs_s = monotonic()

    # --- Callbacks des services ---

    def _gerer_stop_moteurs_callback(
        self,
        _requete: object,
        reponse: Trigger.Response,
    ) -> Trigger.Response:
        """
        Demande l'arrêt moteur et mémorise une consigne des moteurs nulle.
        """

        self._memoriser_arret_moteurs()
        if not self._verifier_liaison_serie():
            self._remplir_reponse_service_indisponible(reponse, 'STOP_MOT')
            return reponse

        try:
            self.transport.stop_moteurs()
            confirmation = self._attendre_reponse_attendue('OK STOP_MOT')
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Commande STOP_MOT impossible : {erreur}')
            self._remplir_reponse_service_erreur(reponse, 'STOP_MOT', erreur)
            return reponse

        self._remplir_reponse_service_confirmation(
            reponse,
            'STOP_MOT',
            'OK STOP_MOT',
            confirmation,
        )
        return reponse

    def _gerer_ping_callback(self, _requete: object, reponse: Trigger.Response) -> Trigger.Response:
        """
        Envoie `PING` et attend la réponse `OK PING` du Pico.
        """

        if not self._verifier_liaison_serie():
            self._remplir_reponse_service_indisponible(reponse, 'PING')
            return reponse

        try:
            self.transport.ping()
            confirmation = self._attendre_reponse_attendue('OK PING')
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Commande PING impossible : {erreur}')
            self._remplir_reponse_service_erreur(reponse, 'PING', erreur)
            return reponse

        self._remplir_reponse_service_confirmation(
            reponse,
            'PING',
            'OK PING',
            confirmation,
        )
        return reponse

    def _gerer_reset_encodeurs_callback(
        self,
        _requete: object,
        reponse: Trigger.Response,
    ) -> Trigger.Response:
        """
        Demande la remise à zéro des compteurs d'encodeurs du Pico.
        """

        if not self._verifier_liaison_serie():
            self._remplir_reponse_service_indisponible(reponse, 'RESET_ENC')
            return reponse

        try:
            self.transport.reset_encodeurs()
            confirmation = self._attendre_reponse_attendue('OK RESET_ENC')
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Commande RESET_ENC impossible : {erreur}')
            self._remplir_reponse_service_erreur(reponse, 'RESET_ENC', erreur)
            return reponse

        self._remplir_reponse_service_confirmation(
            reponse,
            'RESET_ENC',
            'OK RESET_ENC',
            confirmation,
        )
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
            self._signaler_erreur_uart(f'Demande de distance impossible : {erreur}')

    def _demander_encodeurs_callback(self) -> None:
        """
        Demande périodiquement les compteurs d'encodeurs au Pico.
        """

        if not self._verifier_liaison_serie():
            return

        try:
            self.transport.demander_encodeurs()
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Demande des encodeurs impossible : {erreur}')

    def _maintenir_derniere_consigne_moteurs_callback(self) -> None:
        """
        Répète temporairement la dernière consigne valide avant le timeout du Pico.
        """

        if self.derniere_consigne_moteurs is None:
            return
        if not self._verifier_liaison_serie():
            return

        gauche, droite = self.derniere_consigne_moteurs
        if (
            (gauche != 0 or droite != 0)
            and (
                self.instant_derniere_consigne_moteurs_s is None
                or monotonic() - self.instant_derniere_consigne_moteurs_s
                > self.delai_expiration_consigne_moteurs_s
            )
        ):
            self.get_logger().warn(
                'Consigne moteur ROS expirée : arrêt explicite envoyé au Pico.'
            )
            self._memoriser_arret_moteurs()
            gauche, droite = self.derniere_consigne_moteurs

        try:
            self.transport.set_moteurs(gauche, droite)
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(
                f'Maintien de consigne des moteurs impossible : {erreur}'
            )

    def _lire_et_traiter_reponse_uart_callback(self) -> None:
        """
        Publie en ROS 2 toute ligne texte éventuellement renvoyée par le Pico.
        """

        if not self._verifier_liaison_serie():
            return
        try:
            ligne = self.transport.lire_ligne()
        except (serial.SerialException, OSError) as erreur:
            self._signaler_erreur_uart(f'Lecture UART impossible : {erreur}')
            return

        if not ligne:
            return

        self._traiter_ligne_uart(ligne)

    # --- Méthodes privées utilitaires ---

    def _attendre_reponse_attendue(self, reponse_attendue: str) -> bool:
        """
        Attend brièvement une réponse précise sans avaler les événements spontanés.
        """

        fin_attente_s = monotonic() + self.delai_attente_reponse_service_s
        while monotonic() < fin_attente_s:
            ligne = self.transport.lire_ligne()
            if not ligne:
                continue

            reponse_recue = self._traiter_ligne_uart(ligne)
            if reponse_recue == reponse_attendue:
                return True

        return False

    def _traiter_ligne_uart(self, ligne: str) -> str | None:
        """
        Publie une ligne Pico et décode les réponses normalisées utiles à ROS 2.
        """

        message = String()
        message.data = ligne
        self.publisher_etat.publish(message)

        morceaux = ligne.split()
        if not morceaux:
            return None

        if ligne == 'READY':
            self.get_logger().info('Événement spontané du Pico : READY')
            return None
        if ligne == 'AVERT TIMEOUT':
            self.get_logger().warn('Événement spontané du Pico : AVERT TIMEOUT')
            return None
        if morceaux[0] == 'OK':
            return self._traiter_reponse_ok(morceaux, ligne)
        if morceaux[0] in ('AVERT', 'WARN'):
            self.get_logger().warn(f'Réponse UART du Pico : {ligne}')
            return None
        if morceaux[0] == 'ERREUR':
            self.get_logger().error(f'Réponse UART du Pico : {ligne}')
            return None

        self.get_logger().debug(f'Réponse UART du Pico : {ligne}')
        return None

    def _remplir_reponse_service_confirmation(
        self,
        reponse: Trigger.Response,
        commande: str,
        confirmation_attendue: str,
        confirmation: bool,
    ) -> None:
        """
        Applique le même format de succès ou d'échec pour les services Pico.
        """

        reponse.success = confirmation
        if confirmation:
            reponse.message = f'{confirmation_attendue} confirmé par le Pico.'
        else:
            reponse.message = (
                f'Échec {commande} : confirmation {confirmation_attendue} '
                'non reçue dans le délai.'
            )

    def _remplir_reponse_service_indisponible(
        self,
        reponse: Trigger.Response,
        commande: str,
    ) -> None:
        """
        Signale un service Pico impossible parce que la liaison UART est indisponible.
        """

        reponse.success = False
        reponse.message = f'Échec {commande} : liaison UART indisponible.'

    def _remplir_reponse_service_erreur(
        self,
        reponse: Trigger.Response,
        commande: str,
        erreur: serial.SerialException | OSError,
    ) -> None:
        """
        Signale un service Pico interrompu par une erreur UART.
        """

        reponse.success = False
        reponse.message = f'Échec {commande} : {erreur}'

    def _traiter_reponse_ok(self, morceaux: list[str], ligne: str) -> str | None:
        """
        Décode une réponse `OK ...` du protocole UART Pico courant.
        """

        if len(morceaux) < 2:
            self.get_logger().warn(f'Réponse OK incomplète du Pico : {ligne}')
            return None

        commande = morceaux[1]
        if commande == 'PING' and len(morceaux) == 2:
            self.get_logger().debug('Réponse OK PING reçue du Pico.')
            return 'OK PING'
        if commande == 'STOP_MOT' and len(morceaux) == 2:
            self.get_logger().debug('Réponse OK STOP_MOT reçue du Pico.')
            return 'OK STOP_MOT'
        if commande == 'RESET_ENC' and len(morceaux) == 2:
            self.get_logger().debug('Réponse OK RESET_ENC reçue du Pico.')
            return 'OK RESET_ENC'
        if commande == 'SET_MOT' and len(morceaux) == 4:
            return self._traiter_reponse_set_mot(morceaux, ligne)
        if commande == 'SET_SERVO' and len(morceaux) == 3:
            return self._traiter_reponse_set_servo(morceaux, ligne)
        if commande == 'SONAR' and len(morceaux) == 3:
            return self._traiter_reponse_sonar(morceaux, ligne)
        if commande == 'ENC' and len(morceaux) == 4:
            return self._traiter_reponse_encodeurs(morceaux, ligne)
        if commande == 'STATUS' and len(morceaux) == 5:
            return self._traiter_reponse_status(morceaux, ligne)

        self.get_logger().warn(f'Réponse OK non reconnue du Pico : {ligne}')
        return None

    def _traiter_reponse_set_mot(self, morceaux: list[str], ligne: str) -> str | None:
        """
        Valide la réponse à une consigne moteur sans republier la commande.
        """

        try:
            int(morceaux[2])
            int(morceaux[3])
        except ValueError:
            self.get_logger().warn(f'Réponse SET_MOT invalide du Pico : {ligne}')
            return None

        self.get_logger().debug(f'Réponse UART du Pico : {ligne}')
        return 'OK SET_MOT'

    def _traiter_reponse_set_servo(self, morceaux: list[str], ligne: str) -> str | None:
        """
        Valide la réponse à une consigne de servo.
        """

        try:
            int(morceaux[2])
        except ValueError:
            self.get_logger().warn(f'Réponse SET_SERVO invalide du Pico : {ligne}')
            return None

        self.get_logger().debug(f'Réponse UART du Pico : {ligne}')
        return 'OK SET_SERVO'

    def _traiter_reponse_sonar(self, morceaux: list[str], ligne: str) -> str | None:
        """
        Publie la distance sonar reçue du Pico.
        """

        try:
            distance_mm = int(morceaux[2])
        except ValueError:
            self.get_logger().warn(f'Réponse SONAR invalide du Pico : {ligne}')
            return None

        message_distance = Int32()
        message_distance.data = distance_mm
        self.publisher_distance.publish(message_distance)
        return 'OK SONAR'

    def _traiter_reponse_encodeurs(self, morceaux: list[str], ligne: str) -> str | None:
        """
        Publie les compteurs d'encodeurs reçus du Pico.
        """

        try:
            gauche_ticks = int(morceaux[2])
            droite_ticks = int(morceaux[3])
        except ValueError:
            self.get_logger().warn(f'Réponse ENC invalide du Pico : {ligne}')
            return None

        message_encodeurs = EtatEncodeurs()
        message_encodeurs.gauche_ticks = gauche_ticks
        message_encodeurs.droite_ticks = droite_ticks
        self.publisher_encodeurs.publish(message_encodeurs)
        return 'OK ENC'

    def _traiter_reponse_status(self, morceaux: list[str], ligne: str) -> str | None:
        """
        Valide la réponse d'état moteur sans créer de diagnostic supplémentaire.
        """

        try:
            int(morceaux[2])
            int(morceaux[3])
            actif = int(morceaux[4])
        except ValueError:
            self.get_logger().warn(f'Réponse STATUS invalide du Pico : {ligne}')
            return None

        if actif not in (0, 1):
            self.get_logger().warn(f'Réponse STATUS avec actif inattendu : {ligne}')
            return None

        self.get_logger().debug(f'Réponse UART du Pico : {ligne}')
        return 'OK STATUS'

    def _memoriser_arret_moteurs(self) -> None:
        """
        Remplace toute ancienne consigne moteur par un arrêt sécuritaire.
        """

        self.derniere_consigne_moteurs = (0, 0)
        self.instant_derniere_consigne_moteurs_s = None

    def _signaler_erreur_uart(self, message: str) -> None:
        """
        Ferme le port après une erreur UART déjà expliquée dans les logs.
        """

        self._memoriser_arret_moteurs()
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
            if not self._uart_disponible:
                self.transport.stop_moteurs()
        except (serial.SerialException, OSError) as erreur:
            if self._uart_disponible:
                self.get_logger().error(f'Liaison UART perdue : {erreur}')
            elif not self._indisponibilite_uart_journalisee:
                self.get_logger().warn(
                    f'Liaison UART indisponible au démarrage ou en reprise : {erreur}'
                )
            self._memoriser_arret_moteurs()
            self.transport.fermer()
            self._uart_disponible = False
            self._indisponibilite_uart_journalisee = True
            return False

        if not self._uart_disponible:
            self._memoriser_arret_moteurs()
            self.get_logger().info(
                f'Interface Pico ouverte sur {self.port} à {self.debit} bauds '
                'avec arrêt moteur.'
            )
        self._uart_disponible = True
        self._indisponibilite_uart_journalisee = False
        return True

    # --- Cycle de vie du nœud ---

    def destroy_node(self) -> bool:
        """
        Demande l'arrêt moteur puis ferme le port série avant l'arrêt complet du nœud.
        """

        self._memoriser_arret_moteurs()
        try:
            self.transport.stop_moteurs()
        except (serial.SerialException, OSError) as erreur:
            self.get_logger().error(
                f'Commande STOP_MOT impossible pendant la fermeture : {erreur}'
            )
        finally:
            self.transport.fermer()

        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """
    Initialise ROS 2 puis exécute le nœud jusqu'à son arrêt.
    """

    rclpy.init(args=args)
    noeud: InterfacePico | None = None

    try:
        noeud = InterfacePico()
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
