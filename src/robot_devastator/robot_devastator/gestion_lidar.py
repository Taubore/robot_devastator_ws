# -*- coding: utf-8 -*-
"""Pont ROS 2 vers rplidar_composition : centralise l'état veille/actif du RPLIDAR."""

from __future__ import annotations

import signal
from types import FrameType
from typing import Final

import rclpy
from rclpy.client import Client
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_srvs.srv import Empty as ServiceVide
from std_srvs.srv import Trigger

DELAI_REVEIL_EXECUTEUR_S: Final[float] = 0.2
SERVICE_ACTIVER_LIDAR: Final[str] = '/activer_lidar'
SERVICE_DESACTIVER_LIDAR: Final[str] = '/desactiver_lidar'
SERVICE_DEMARRAGE_LIDAR: Final[str] = '/start_motor'
SERVICE_ARRET_LIDAR: Final[str] = '/stop_motor'


def _interrompre_execution(
    _numero_signal: int,
    _frame: FrameType | None,
) -> None:
    """Interrompt proprement l'exécution lors d'une demande d'arrêt système."""
    raise KeyboardInterrupt


class GestionLidar(Node):
    """Centralise l'état du RPLIDAR pour que toute source (manuel, futur autonome) le partage."""

    def __init__(self) -> None:
        super().__init__('gestion_lidar')

        # Dormance par défaut, cohérente avec la Phase 9 : aucune source ne doit supposer
        # que le RPLIDAR est actif tant qu'elle n'a pas appelé activer_lidar.
        self.lidar_actif = False

        self.client_demarrage = self.create_client(ServiceVide, SERVICE_DEMARRAGE_LIDAR)
        self.client_arret = self.create_client(ServiceVide, SERVICE_ARRET_LIDAR)
        self.service_activer = self.create_service(
            Trigger,
            SERVICE_ACTIVER_LIDAR,
            self._gerer_activer_lidar_callback,
        )
        self.service_desactiver = self.create_service(
            Trigger,
            SERVICE_DESACTIVER_LIDAR,
            self._gerer_desactiver_lidar_callback,
        )

        self._forcer_dormance_au_demarrage()
        self.get_logger().info(
            f"Prêt ; services '{SERVICE_ACTIVER_LIDAR}' et '{SERVICE_DESACTIVER_LIDAR}' ouverts."
        )

    # --- Callbacks des services ---

    def _gerer_activer_lidar_callback(
        self,
        _requete: object,
        reponse: Trigger.Response,
    ) -> Trigger.Response:
        """Démarre le RPLIDAR via /start_motor et marque le lidar actif."""
        return self._basculer_lidar(
            actif_souhaite=True,
            client=self.client_demarrage,
            reponse=reponse,
        )

    def _gerer_desactiver_lidar_callback(
        self,
        _requete: object,
        reponse: Trigger.Response,
    ) -> Trigger.Response:
        """Arrête le RPLIDAR via /stop_motor et marque le lidar en dormance."""
        return self._basculer_lidar(
            actif_souhaite=False,
            client=self.client_arret,
            reponse=reponse,
        )

    # --- Méthodes privées utilitaires ---

    def _basculer_lidar(
        self,
        *,
        actif_souhaite: bool,
        client: Client,
        reponse: Trigger.Response,
    ) -> Trigger.Response:
        """Relaie la demande vers rplidar_composition et met à jour l'état interne."""
        if not client.service_is_ready():
            reponse.success = False
            reponse.message = f"Service '{client.srv_name}' indisponible."
            self.get_logger().warning(reponse.message)
            return reponse

        # Appel non bloquant : la réponse de rplidar_composition n'est pas attendue ici,
        # le nœud ne spin pas de futur pendant un callback de service.
        client.call_async(ServiceVide.Request())
        self.lidar_actif = actif_souhaite

        etat = 'actif' if actif_souhaite else 'en dormance'
        reponse.success = True
        reponse.message = f'RPLIDAR {etat}.'
        self.get_logger().info(reponse.message)
        return reponse

    def _forcer_dormance_au_demarrage(self) -> None:
        """Appelle /stop_motor une fois, peu importe l'état initial de rplidar_composition."""
        self.get_logger().info(
            f"Attente du service '{SERVICE_ARRET_LIDAR}' pour forcer la dormance initiale..."
        )
        # Attente bloquante et sans délai : le lancement ordonne gestion_lidar après
        # rplidar_composition, et le robot ne doit jamais démarrer avec le lidar actif.
        # Un seul appel suffit : rplidar_composition envoie sa commande de démarrage interne
        # à la fin de son initialisation, bien avant que ce nœud Python soit prêt.
        self.client_arret.wait_for_service()
        futur = self.client_arret.call_async(ServiceVide.Request())
        rclpy.spin_until_future_complete(self, futur)

        self.lidar_actif = False
        self.get_logger().info('RPLIDAR mis en dormance au démarrage.')


def main(args: list[str] | None = None) -> None:
    """
    Lance gestion_lidar jusqu'à la demande d'arrêt.

    Aucun /stop_motor final n'est tenté : le moteur du A1 est commandé par la ligne DTR du
    convertisseur USB-série, que Linux relâche quand rplidar_composition ferme le port en
    quittant. L'appel serait donc annulé et son log faussement rassurant, comme mesuré sur le
    Raspberry Pi 4 (voir docs/decisions_et_lecons.md).
    """
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, _interrompre_execution)
    signal.signal(signal.SIGTERM, _interrompre_execution)

    noeud: GestionLidar | None = None
    try:
        noeud = GestionLidar()
        while rclpy.ok():
            rclpy.spin_once(noeud, timeout_sec=DELAI_REVEIL_EXECUTEUR_S)
    except KeyboardInterrupt:
        if noeud is not None:
            noeud.get_logger().info("Arrêt demandé par l'utilisateur.")
    finally:
        try:
            if noeud is not None:
                noeud.destroy_node()
        finally:
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == '__main__':
    main()
