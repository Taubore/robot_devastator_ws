# Devastator

Workspace ROS 2 du projet Devastator pour la cible Raspberry Pi 4.

## Environnement

- ROS 2 Jazzy
- Ubuntu 24.04
- Raspberry Pi 4

## Contenu

- `src/commun` : interfaces ROS 2
- `src/robot_devastator` : package Python principal

## Construction

```bash
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

## Structure

- `src/` : sources du workspace
- `build/` : fichiers de compilation générés
- `install/` : artefacts d'installation
- `log/` : journaux de build
