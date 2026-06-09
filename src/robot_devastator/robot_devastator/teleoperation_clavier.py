# -*- coding: utf-8 -*-
"""Téléopère Devastator au clavier en publiant des consignes moteur bornées."""

from __future__ import annotations

import argparse
import select
import sys
import termios
import time
import tty
from types import TracebackType
from typing import Final, TextIO

from commun.msg import ConsigneMoteurs
import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args

DELAI_ATTENTE_ABONNE_S: Final[float] = 2.0
DELAI_INACTIVITE_PAR_DEFAUT_S: Final[float] = 0.45
INTERVALLE_ARRET_S: Final[float] = 0.1
NOMBRE_PUBLICATIONS_ARRET: Final[int] = 4
PERIODE_PUBLICATION_PAR_DEFAUT_S: Final[float] = 0.1
TOPIC_COMMANDE_MOTEURS: Final[str] = '/pico/commande_moteurs'
VITESSE_MAX_AUTORISEE: Final[int] = 500
VITESSE_PAR_DEFAUT: Final[int] = 250


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


class TeleoperationClavier(Node):
    """Publie des commandes moteur manuelles tant que le clavier reste actif."""

    def __init__(
        self,
        vitesse: int,
        delai_inactivite_s: float,
        periode_publication_s: float,
        entree: TextIO,
    ) -> None:
        super().__init__('teleoperation_clavier')

        self.vitesse = vitesse
        self.delai_inactivite_s = delai_inactivite_s
        self.periode_publication_s = periode_publication_s
        self.entree = entree
        self.consigne_gauche = 0
        self.consigne_droite = 0
        self.derniere_touche_s = time.monotonic()

        self.consigne_moteurs_pub = self.create_publisher(
            ConsigneMoteurs,
            TOPIC_COMMANDE_MOTEURS,
            10,
        )

    def attendre_interface_pico(self) -> None:
        """Attend brièvement que `interface_pico` écoute les commandes moteur."""
        limite_attente_s = time.monotonic() + DELAI_ATTENTE_ABONNE_S
        while (
            self.consigne_moteurs_pub.get_subscription_count() == 0
            and time.monotonic() < limite_attente_s
        ):
            time.sleep(0.1)

        if self.consigne_moteurs_pub.get_subscription_count() == 0:
            raise RuntimeError(
                'Aucun abonné détecté sur /pico/commande_moteurs. '
                "Lancer d'abord interface_pico."
            )

    def executer(self) -> None:
        """Lit le clavier et publie une consigne jusqu'à la demande de sortie."""
        self.get_logger().info(
            'Téléopération clavier prête. Touches QWERTY : w avant, s arrière, '
            'a gauche, d droite, espace stop, x quitter.'
        )
        self.get_logger().info(
            'Garder les roues dans le vide au premier essai. '
            'Sans touche reçue, les moteurs sont arrêtés.'
        )

        with ModeClavierTerminal(self.entree):
            while rclpy.ok():
                touche = self._lire_touche()
                if touche is not None and self._appliquer_touche(touche):
                    break

                if (
                    self.consigne_gauche != 0 or self.consigne_droite != 0
                ) and time.monotonic() - self.derniere_touche_s > self.delai_inactivite_s:
                    self.consigne_gauche = 0
                    self.consigne_droite = 0

                self._publier_consigne(self.consigne_gauche, self.consigne_droite)

    def arreter_moteurs(self) -> None:
        """Publie plusieurs arrêts pour laisser le temps à DDS de transmettre."""
        self.consigne_gauche = 0
        self.consigne_droite = 0
        for _ in range(NOMBRE_PUBLICATIONS_ARRET):
            self._publier_consigne(0, 0)
            time.sleep(INTERVALLE_ARRET_S)
        self.get_logger().info('Arrêt moteur explicite publié.')

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
        """Convertit une touche clavier en consigne moteur."""
        if touche in ('x', '\x03'):
            return True

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

        self.derniere_touche_s = time.monotonic()
        return False

    def _publier_consigne(self, gauche: int, droite: int) -> None:
        """Publie une consigne moteur déjà bornée par la configuration CLI."""
        message = ConsigneMoteurs()
        message.gauche = gauche
        message.droite = droite
        self.consigne_moteurs_pub.publish(message)


def _lire_vitesse(valeur: str) -> int:
    """Lit une vitesse faible adaptée aux essais matériels prudents."""
    vitesse = int(valeur)
    if not 1 <= abs(vitesse) <= VITESSE_MAX_AUTORISEE:
        raise argparse.ArgumentTypeError(
            f'la vitesse doit être comprise entre 1 et {VITESSE_MAX_AUTORISEE}'
        )
    return abs(vitesse)


def _lire_delai_inactivite(valeur: str) -> float:
    """Lit le délai après lequel l'absence de touche force l'arrêt."""
    delai_s = float(valeur)
    if not 0.2 <= delai_s <= 2.0:
        raise argparse.ArgumentTypeError('le délai doit être compris entre 0.2 s et 2.0 s')
    return delai_s


def _creer_analyseur_arguments() -> argparse.ArgumentParser:
    """Crée les options CLI volontairement limitées de la téléopération."""
    analyseur = argparse.ArgumentParser(
        description='Téléopère Devastator au clavier avec arrêt automatique.'
    )
    analyseur.add_argument(
        '--vitesse',
        default=VITESSE_PAR_DEFAUT,
        type=_lire_vitesse,
        help=f'vitesse moteur limitée à {VITESSE_MAX_AUTORISEE} (défaut : %(default)s)',
    )
    analyseur.add_argument(
        '--delai-inactivite',
        default=DELAI_INACTIVITE_PAR_DEFAUT_S,
        type=_lire_delai_inactivite,
        help='délai sans touche avant arrêt, en secondes (défaut : %(default)s)',
    )
    return analyseur


def main(args: list[str] | None = None) -> None:
    """Lance la téléopération clavier et garantit un arrêt moteur à la sortie."""
    arguments = _creer_analyseur_arguments().parse_args(remove_ros_args(args=args)[1:])

    rclpy.init(args=args)
    noeud = TeleoperationClavier(
        vitesse=arguments.vitesse,
        delai_inactivite_s=arguments.delai_inactivite,
        periode_publication_s=PERIODE_PUBLICATION_PAR_DEFAUT_S,
        entree=sys.stdin,
    )

    try:
        noeud.attendre_interface_pico()
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
