# -*- coding: utf-8 -*-
"""
Effectue un essai moteur ROS 2 court avec un arrêt explicite garanti.
"""

from __future__ import annotations

import argparse
import time
from typing import Final

import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args

from commun.msg import ConsigneMoteurs

DUREE_MAX_S: Final[float] = 2.0
DUREE_PAR_DEFAUT_S: Final[float] = 1.0
INTERVALLE_ARRET_S: Final[float] = 0.1
NOMBRE_PUBLICATIONS_ARRET: Final[int] = 3
TOPIC_COMMANDE_MOTEURS: Final[str] = '/pico/commande_moteurs'
VITESSE_MAX_ESSAI: Final[int] = 300
VITESSE_PAR_DEFAUT: Final[int] = 300


def _lire_duree(valeur: str) -> float:
    """
    Valide une durée d'essai volontairement courte.
    """
    duree = float(valeur)
    if not 0.0 < duree <= DUREE_MAX_S:
        raise argparse.ArgumentTypeError(
            f'la durée doit être supérieure à 0 et inférieure ou égale à {DUREE_MAX_S}'
        )
    return duree


def _lire_vitesse(valeur: str) -> int:
    """
    Valide une vitesse faible adaptée à un premier essai roues dans le vide.
    """
    vitesse = int(valeur)
    if vitesse == 0 or abs(vitesse) > VITESSE_MAX_ESSAI:
        raise argparse.ArgumentTypeError(
            f'la vitesse doit être non nulle et comprise entre -{VITESSE_MAX_ESSAI} '
            f'et {VITESSE_MAX_ESSAI}'
        )
    return vitesse


def _creer_analyseur_arguments() -> argparse.ArgumentParser:
    """
    Crée les options limitées de l'essai moteur manuel.
    """
    analyseur = argparse.ArgumentParser(
        description='Teste brièvement les deux moteurs puis publie un arrêt explicite.'
    )
    analyseur.add_argument(
        '--duree',
        default=DUREE_PAR_DEFAUT_S,
        type=_lire_duree,
        help=f'durée en secondes, maximum {DUREE_MAX_S} (défaut: %(default)s)',
    )
    analyseur.add_argument(
        '--vitesse',
        default=VITESSE_PAR_DEFAUT,
        type=_lire_vitesse,
        help=f'consigne commune limitée à ±{VITESSE_MAX_ESSAI} (défaut: %(default)s)',
    )
    return analyseur


def main(args: list[str] | None = None) -> None:
    """
    Publie une consigne bornée et garantit ensuite un arrêt moteur explicite.
    """
    arguments = _creer_analyseur_arguments().parse_args(remove_ros_args(args=args)[1:])
    rclpy.init(args=args)
    noeud = Node('essai_moteurs_borne')
    publication = noeud.create_publisher(ConsigneMoteurs, TOPIC_COMMANDE_MOTEURS, 10)

    try:
        # Attendre brièvement la découverte DDS évite de perdre la consigne de test.
        limite_attente = time.monotonic() + 2.0
        while publication.get_subscription_count() == 0 and time.monotonic() < limite_attente:
            time.sleep(0.1)

        if publication.get_subscription_count() == 0:
            raise RuntimeError(
                "Aucun abonné détecté. Lancer d'abord interface_pico_node, puis recommencer."
            )

        consigne = ConsigneMoteurs()
        consigne.gauche = arguments.vitesse
        consigne.droite = arguments.vitesse
        noeud.get_logger().info(
            f'Essai moteur à {arguments.vitesse} pendant {arguments.duree:.1f} s. '
            'Les roues doivent être dans le vide.'
        )
        publication.publish(consigne)
        time.sleep(arguments.duree)
    finally:
        # Répéter l'arrêt laisse le temps à DDS de transmettre la consigne avant la fermeture.
        arret = ConsigneMoteurs()
        arret.gauche = 0
        arret.droite = 0
        for _ in range(NOMBRE_PUBLICATIONS_ARRET):
            publication.publish(arret)
            time.sleep(INTERVALLE_ARRET_S)
        noeud.get_logger().info('Arrêt moteur explicite publié.')
        noeud.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
