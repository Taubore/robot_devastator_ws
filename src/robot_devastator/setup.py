from setuptools import find_packages, setup

package_name = 'robot_devastator'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=
    [
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='taubore',
    maintainer_email='louis.st-hilaire@hotmail.com',
    description='Package ROS 2 Python pour piloter le robot Devastator et tester la synthese vocale avec Piper',
    license='MIT',
    tests_require=['pytest'],
    entry_points=
    {
        'console_scripts': 
        [
            'principal = robot_devastator.principal:main',
            'voix_piper_service = robot_devastator.voix_piper_service:main',
        ],
    },
)
