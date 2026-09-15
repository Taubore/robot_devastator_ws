"""Publie l'état du robot (TF, /robot_description) à partir du xacro Devastator.

Isolé dans un fichier .launch.py distinct : $(command 'xacro ...') en YAML fait planter
l'inférence de type de launch_yaml sur les commentaires du xacro généré (typographie
française « mot : mot »), voir docs/decisions_et_lecons.md.
"""

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import os


def generate_launch_description():
    pkg_share = get_package_share_directory('robot_devastator_description')
    xacro_file = os.path.join(pkg_share, 'urdf', 'devastator.urdf.xacro')

    robot_description = xacro.process_file(xacro_file).toxml()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )

    return LaunchDescription([robot_state_publisher])
