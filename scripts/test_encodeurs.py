# -*- coding: utf-8 -*-
"""
Script de diagnostic autonome pour valider la chaîne ROS 2 des encodeurs.

S'abonne à /pico/encodeurs et affiche les ticks cumulés, les deltas et les
vitesses estimées à chaque message reçu. Ne publie aucune commande.

Usage :
    source install/setup.bash
    python3 scripts/test_encodeurs.py
"""

from __future__ import annotations

from typing import Final

import rclpy
from rclpy.node import Node
from rclpy.time import Time

from commun.msg import EtatEncodeurs

TOPIC_ENCODEURS: Final[str] = '/pico/encodeurs'
TAILLE_FILE_MESSAGES: Final[int] = 10


class DiagnosticEncodeurs(Node):
    """
    Affiche les ticks cumulés, les deltas et les vitesses estimées des encodeurs.

    Lecture seule — aucune commande moteur ni publication. La durée écoulée
    entre les messages est mesurée via l'horloge ROS 2.
    """

    def __init__(self) -> None:
        super().__init__('diagnostic_encodeurs')

        # État mémorisé entre deux messages consécutifs
        self._ticks_precedents: tuple[int, int] | None = None
        self._instant_precedent: Time | None = None

        self._abonnement = self.create_subscription(
            EtatEncodeurs,
            TOPIC_ENCODEURS,
            self._encodeurs_callback,
            TAILLE_FILE_MESSAGES,
        )

        self.get_logger().info(
            f"Diagnostic encodeurs démarré — abonné à '{TOPIC_ENCODEURS}'."
        )

    # --- Callbacks des subscriptions ---

    def _encodeurs_callback(self, message: EtatEncodeurs) -> None:
        """
        Affiche les ticks, deltas et vitesses à chaque message reçu.
        """

        gauche = message.gauche_ticks
        droite = message.droite_ticks
        maintenant = self.get_clock().now()

        if self._ticks_precedents is None:
            # Premier message : initialisation sans affichage de delta
            self._ticks_precedents = (gauche, droite)
            self._instant_precedent = maintenant
            self.get_logger().info(
                f'Premier message reçu — ticks initiaux : gauche={gauche}  droite={droite}'
            )
            return

        gauche_precedent, droite_precedent = self._ticks_precedents

        delta_gauche = gauche - gauche_precedent
        delta_droite = droite - droite_precedent

        # Durée en secondes entre les deux derniers messages via l'horloge ROS 2
        assert self._instant_precedent is not None
        duree_ns = (maintenant - self._instant_precedent).nanoseconds
        duree_s = duree_ns / 1e9

        if duree_s > 0.0:
            vitesse_gauche = delta_gauche / duree_s
            vitesse_droite = delta_droite / duree_s
        else:
            vitesse_gauche = 0.0
            vitesse_droite = 0.0

        self.get_logger().info(
            f'Ticks : G={gauche:>8}  D={droite:>8}  |  '
            f'Delta : G={delta_gauche:>+6}  D={delta_droite:>+6}  |  '
            f'Vitesse (ticks/s) : G={vitesse_gauche:>+8.1f}  D={vitesse_droite:>+8.1f}'
        )

        self._ticks_precedents = (gauche, droite)
        self._instant_precedent = maintenant


def main(args: list[str] | None = None) -> None:
    """
    Initialise ROS 2 puis exécute le nœud jusqu'à son arrêt.
    """

    rclpy.init(args=args)
    noeud: DiagnosticEncodeurs | None = None

    try:
        noeud = DiagnosticEncodeurs()
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
