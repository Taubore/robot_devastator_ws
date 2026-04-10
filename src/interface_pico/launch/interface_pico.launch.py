"""Lancement minimal du nœud interface_pico."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Crée la description de lancement minimale."""
    return LaunchDescription(
        [
            Node(
                package='interface_pico',
                executable='interface_pico_node',
                name='interface_pico_node',
                output='screen',
            ),
        ]
    )
