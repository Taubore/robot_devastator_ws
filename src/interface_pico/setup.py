"""Décrit l'installation du package ROS 2 Python interface_pico."""

from glob import glob

from setuptools import find_packages, setup

package_name = 'interface_pico'

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
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='taubore',
    maintainer_email='louis.st-hilaire@hotmail.com',
    description='Nœud ROS 2 simple pour dialoguer en UART avec le Raspberry Pi Pico WH',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'interface_pico_node = interface_pico.interface_pico:main',
        ],
    },
)
