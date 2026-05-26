"""Lancement minimal du nœud interface_pico."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Crée la description de lancement minimale."""
    mode_materiel = LaunchConfiguration('mode_materiel')

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'mode_materiel',
                default_value='reel',
                description="Mode matériel : reel ou simulation.",
            ),
            Node(
                package='interface_pico',
                executable='interface_pico_node',
                name='interface_pico_node',
                output='screen',
                parameters=[
                    {
                        'mode_materiel': mode_materiel,
                    }
                ],
            ),
        ]
    )
