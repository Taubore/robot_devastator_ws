"""Lance rplidar_composition et gestion_lidar avec un arrêt de fermeture ordonné.

Isolé dans un fichier .launch.py distinct : YAML ne permet pas d'accrocher une action au
Shutdown global du launch. Sans ce séquencement, `ros2 launch` envoie SIGINT à tous les nœuds
en parallèle ; rplidar_composition (nœud C++) détruit son service /stop_motor plus vite que
gestion_lidar (Python/rclpy) ne peut réagir, donc l'appel de fermeture de gestion_lidar arrive
systématiquement trop tard. Voir docs/decisions_et_lecons.md pour le détail du problème observé.

Le gestionnaire OnShutdown ci-dessous appelle /desactiver_lidar de façon bloquante avant de
laisser le launch poursuivre sa séquence normale d'arrêt (SIGINT à tous les nœuds, dont
rplidar_composition), ce qui garantit que la demande d'arrêt part avant que le service ne
disparaisse.
"""

import subprocess

from launch import LaunchDescription
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnShutdown

from launch_ros.actions import Node

DELAI_ARRET_LIDAR_S = 2.0
SERIAL_PORT_RPLIDAR = (
    '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'
)


def _arreter_lidar_avant_fermeture(_event, _context):
    """Bloque la séquence de fermeture du launch le temps de mettre le RPLIDAR en dormance."""
    print('[rplidar_gestion_lidar] Arrêt ordonné : mise en dormance avant fermeture des nœuds.')
    try:
        subprocess.run(
            ['ros2', 'service', 'call', '/desactiver_lidar', 'std_srvs/srv/Trigger'],
            timeout=DELAI_ARRET_LIDAR_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print('[rplidar_gestion_lidar] /desactiver_lidar sans réponse à temps, on poursuit.')
    except FileNotFoundError:
        print('[rplidar_gestion_lidar] Commande ros2 introuvable, mise en dormance ignorée.')


def generate_launch_description():
    """Décrit les nœuds rplidar_composition et gestion_lidar avec leur arrêt ordonné."""
    rplidar_composition = Node(
        package='rplidar_ros',
        executable='rplidar_composition',
        name='rplidar_composition',
        output='screen',
        parameters=[{
            'serial_port': SERIAL_PORT_RPLIDAR,
            'frame_id': 'laser_link',
        }],
    )
    gestion_lidar = Node(
        package='robot_devastator',
        executable='gestion_lidar',
        name='gestion_lidar',
        output='screen',
    )

    return LaunchDescription([
        rplidar_composition,
        gestion_lidar,
        RegisterEventHandler(OnShutdown(on_shutdown=_arreter_lidar_avant_fermeture)),
    ])
