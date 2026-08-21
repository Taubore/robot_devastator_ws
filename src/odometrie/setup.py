"""Décrit l'installation du package ROS 2 Python odometrie."""

from setuptools import find_packages, setup

package_name = 'odometrie'

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
    description="Nœud ROS 2 qui calcule et publie l'odométrie du robot Devastator",
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'odometrie = odometrie.odometrie:main',
        ],
    },
)
