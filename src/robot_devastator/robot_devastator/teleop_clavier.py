# -*- coding: utf-8 -*-
"""Téléopère Devastator au clavier en passant par l'arbitre moteur."""

from __future__ import annotations

import select
import signal
import sys
import termios
import time
import tty
from types import FrameType, TracebackType
from typing import Final, TextIO

from commun.msg import ConsigneMoteurs
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String

DELAI_ATTENTE_ABONNE_S: Final[float] = 2.0
INTERVALLE_ARRET_S: Final[float] = 0.1
MODE_AUTONOMIE: Final[str] = 'autonomie'
MODE_MANUEL: Final[str] = 'manuel'
NOMBRE_PUBLICATIONS_ARRET: Final[int] = 4
TOPIC_COMMANDE_MANUELLE: Final[str] = '/robot/commande_moteurs/manuelle'
TOPIC_MODE_CONDUITE: Final[str] = '/robot/mode_conduite'


def _interrompre_execution(
    _numero_signal: int,
    _frame: FrameType | None,
) -> None:
    """Interrompt proprement l'exécution lors d'une demande d'arrêt système."""
    raise KeyboardInterrupt


class ModeClavierTerminal:
    """Passe temporairement le terminal en lecture caractère par caractère."""

    def __init__(self, entree: TextIO) -> None:
        self.entree = entree
        self.descripteur = entree.fileno()
        self.reglages_originaux: list[int | list[bytes | int]] | None = None

    def __enter__(self) -> ModeClavierTerminal:
        if not self.entree.isatty():
            raise RuntimeError('La téléopération clavier demande un terminal interactif.')

        self.reglages_originaux = termios.tcgetattr(self.descripteur)
        tty.setcbreak(self.descripteur)
        return self

    def __exit__(
        self,
        _type_exception: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        if self.reglages_originaux is not None:
            termios.tcsetattr(
                self.descripteur,
                termios.TCSADRAIN,
                self.reglages_originaux,
            )


class TeleopClavier(Node):
    """Publie les commandes clavier manuelles et le mode de conduite demandé."""

    def __init__(self, entree: TextIO) -> None:
        super().__init__('teleop_clavier')

        self.declare_parameter('vitesse_initiale', 200)
        self.declare_parameter('vitesse_min', 100)
        self.declare_parameter('vitesse_max', 500)
        self.declare_parameter('pas_vitesse', 50)
        self.declare_parameter('periode_publication_s', 0.1)

        self.vitesse_min = int(self.get_parameter('vitesse_min').value)
        self.vitesse_max = int(self.get_parameter('vitesse_max').value)
        self.pas_vitesse = int(self.get_parameter('pas_vitesse').value)
        self.vitesse = int(self.get_parameter('vitesse_initiale').value)
        self.periode_publication_s = float(
            self.get_parameter('periode_publication_s').value
        )

        if self.vitesse_min <= 0:
            raise ValueError("Le paramètre 'vitesse_min' doit être positif.")
        if self.vitesse_max < self.vitesse_min:
            raise ValueError(
                "Le paramètre 'vitesse_max' doit être supérieur ou égal à 'vitesse_min'."
            )
        if self.pas_vitesse <= 0:
            raise ValueError("Le paramètre 'pas_vitesse' doit être positif.")
        if self.periode_publication_s <= 0.0:
            raise ValueError("Le paramètre 'periode_publication_s' doit être positif.")

        self.vitesse = self._borner_vitesse(self.vitesse)
        self.entree = entree
        self.mode = MODE_MANUEL
        self.consigne_gauche = 0
        self.consigne_droite = 0

        self.consigne_manuelle_pub = self.create_publisher(
            ConsigneMoteurs,
            TOPIC_COMMANDE_MANUELLE,
            10,
        )
        self.mode_conduite_pub = self.create_publisher(
            String,
            TOPIC_MODE_CONDUITE,
            10,
        )

    def attendre_arbitre(self) -> None:
        """Attend brièvement que l'arbitre écoute les commandes clavier."""
        limite_attente_s = time.monotonic() + DELAI_ATTENTE_ABONNE_S
        while (
            (
                self.consigne_manuelle_pub.get_subscription_count() == 0
                or self.mode_conduite_pub.get_subscription_count() == 0
            )
            and time.monotonic() < limite_attente_s
        ):
            time.sleep(0.1)

        if self.consigne_manuelle_pub.get_subscription_count() == 0:
            raise RuntimeError(
                'Aucun arbitre détecté sur /robot/commande_moteurs/manuelle.'
            )

        if self.mode_conduite_pub.get_subscription_count() == 0:
            raise RuntimeError('Aucun arbitre détecté sur /robot/mode_conduite.')

    def executer(self) -> None:
        """Lit le clavier et publie l'état courant jusqu'à la demande de sortie."""
        self._publier_mode()
        self._afficher_aide()
        self._afficher_etat()

        with ModeClavierTerminal(self.entree):
            while rclpy.ok():
                touche = self._lire_touche()
                if touche is not None and self._appliquer_touche(touche):
                    break

                self._publier_consigne()

    def arreter_moteurs(self) -> None:
        """Publie plusieurs arrêts manuels pour laisser le temps à DDS de transmettre."""
        self.mode = MODE_MANUEL
        self.consigne_gauche = 0
        self.consigne_droite = 0
        self._publier_mode()

        for _ in range(NOMBRE_PUBLICATIONS_ARRET):
            self._publier_consigne()
            time.sleep(INTERVALLE_ARRET_S)

        self.get_logger().info('Arrêt moteur manuel explicite publié.')

    # --- Méthodes privées utilitaires ---

    def _lire_touche(self) -> str | None:
        """Retourne une touche disponible, ou `None` après un court délai."""
        lectures, _, _ = select.select(
            [self.entree],
            [],
            [],
            self.periode_publication_s,
        )
        if not lectures:
            return None

        return self.entree.read(1).lower()

    def _appliquer_touche(self, touche: str) -> bool:
        """Convertit une touche clavier en action de conduite."""
        if touche in ('x', '\x03'):
            return True

        if touche == 'm':
            self._basculer_mode()
            return False

        if touche == '=':
            self._changer_vitesse(self.pas_vitesse)
            return False

        if touche == '-':
            self._changer_vitesse(-self.pas_vitesse)
            return False

        if self.mode != MODE_MANUEL:
            return False

        if touche in (' ', '\n', '\r'):
            self.consigne_gauche = 0
            self.consigne_droite = 0
        elif touche == 'w':
            self.consigne_gauche = self.vitesse
            self.consigne_droite = self.vitesse
        elif touche == 's':
            self.consigne_gauche = -self.vitesse
            self.consigne_droite = -self.vitesse
        elif touche == 'a':
            self.consigne_gauche = -self.vitesse
            self.consigne_droite = self.vitesse
        elif touche == 'd':
            self.consigne_gauche = self.vitesse
            self.consigne_droite = -self.vitesse
        else:
            return False

        self._afficher_etat()
        return False

    def _basculer_mode(self) -> None:
        """Bascule entre conduite manuelle et autonomie simple."""
        self.consigne_gauche = 0
        self.consigne_droite = 0
        if self.mode == MODE_MANUEL:
            self.mode = MODE_AUTONOMIE
        else:
            self.mode = MODE_MANUEL

        self._publier_mode()
        self._afficher_etat()

    def _changer_vitesse(self, variation: int) -> None:
        """Change la vitesse manuelle en respectant les bornes configurées."""
        self.vitesse = self._borner_vitesse(self.vitesse + variation)
        self._afficher_etat()

    def _borner_vitesse(self, vitesse: int) -> int:
        """Limite la vitesse manuelle entre les bornes configurées."""
        return max(self.vitesse_min, min(self.vitesse_max, vitesse))

    def _publier_consigne(self) -> None:
        """Publie une commande manuelle, ou un arrêt lorsque l'autonomie est active."""
        message = ConsigneMoteurs()
        if self.mode == MODE_MANUEL:
            message.gauche = self.consigne_gauche
            message.droite = self.consigne_droite
        else:
            message.gauche = 0
            message.droite = 0

        self.consigne_manuelle_pub.publish(message)

    def _publier_mode(self) -> None:
        """Publie le mode de conduite demandé par le clavier."""
        message = String()
        message.data = self.mode
        self.mode_conduite_pub.publish(message)

    def _afficher_aide(self) -> None:
        """Affiche les commandes clavier utiles dans le terminal."""
        print(
            '\nTéléopération clavier Devastator\n'
            'Touches : w avancer, s reculer, a gauche, d droite, espace stop\n'
            'Vitesse : = augmenter, - diminuer | Mode : m manuel/autonomie | Quitter : x\n'
            'Garder les roues dans le vide au premier essai.\n',
            flush=True,
        )

    def _afficher_etat(self) -> None:
        """Affiche le mode et la vitesse courants."""
        print(
            f'Mode : {self.mode} | vitesse : {self.vitesse} '
            f'| consigne manuelle : {self.consigne_gauche}, {self.consigne_droite}',
            flush=True,
        )


def main(args: list[str] | None = None) -> None:
    """Lance la téléopération clavier et garantit un arrêt moteur à la sortie."""
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, _interrompre_execution)
    signal.signal(signal.SIGTERM, _interrompre_execution)
    noeud = TeleopClavier(entree=sys.stdin)

    try:
        noeud.attendre_arbitre()
        noeud.executer()
    except KeyboardInterrupt:
        pass
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
