"""Décrit l'installation du package Python lcd_st7789v (sans dépendance ROS 2)."""

from setuptools import find_packages, setup

package_name = 'lcd_st7789v'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name, ['README.md']),
        ('share/' + package_name, ['essai_pilote.py']),
        ('share/' + package_name, ['essai_rendu_texte.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='taubore',
    maintainer_email='louis.st-hilaire@hotmail.com',
    description=(
        'Pilote bas niveau et rendu de texte en grille, sans dépendance ROS 2, '
        'pour l\'écran LCD Waveshare 2 pouces (contrôleur ST7789V) sur bus SPI'
    ),
    license='MIT',
    tests_require=['pytest'],
)
