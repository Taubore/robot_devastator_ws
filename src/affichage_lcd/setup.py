"""Décrit l'installation du package ROS 2 Python affichage_lcd."""

from setuptools import find_packages, setup

package_name = 'affichage_lcd'

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
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='taubore',
    maintainer_email='louis.st-hilaire@hotmail.com',
    description=(
        "Nœud ROS 2 d'affichage sur l'écran LCD Waveshare 2 pouces (ST7789V), "
        'troisième couche au-dessus du pilote et du rendu texte de lcd_st7789v'
    ),
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'affichage_lcd = affichage_lcd.affichage_lcd:main',
        ],
    },
)
