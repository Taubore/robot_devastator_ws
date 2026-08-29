"""Décrit l'installation du package ROS 2 Python surveillance_alimentation."""

from setuptools import find_packages, setup

package_name = 'surveillance_alimentation'

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
        'Nœud ROS 2 qui publie tension et courant des batteries et alerte sur '
        'seuil bas, à partir de capteurs INA260 sur bus I2C'
    ),
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'surveillance_alimentation = '
            'surveillance_alimentation.surveillance_alimentation:main',
        ],
    },
)
