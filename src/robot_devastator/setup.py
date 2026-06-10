"""Décrit l'installation du paquet Python ROS 2 robot_devastator."""

from setuptools import find_packages, setup

package_name = 'robot_devastator'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='taubore',
    maintainer_email='louis.st-hilaire@hotmail.com',
    description=(
        'Package ROS 2 Python pour piloter le robot Devastator '
        'et produire les annonces audio avec Piper'
    ),
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'arbitre_commande_moteurs = robot_devastator.arbitre_commande_moteurs:main',
            'evitement_obstacle = robot_devastator.evitement_obstacle:main',
            'teleop_clavier = robot_devastator.teleop_clavier:main',
            'annonces_audio = robot_devastator.annonces_audio:main',
        ],
    },
)
