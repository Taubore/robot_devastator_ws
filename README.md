# Devastator

Workspace ROS 2 du projet Devastator pour la cible Raspberry Pi 4.

## Environnement

- ROS 2 Jazzy
- Ubuntu 24.04
- Raspberry Pi 4

## Contenu

- `src/commun` : interfaces ROS 2
- `src/robot_devastator` : package Python principal

## Services audio

- `generer_audio` : génère un fichier WAV à partir d’un texte
- `jouer_audio` : lit un fichier WAV déjà généré
- Si `nom_fichier` est vide, le fichier utilisé est `/tmp/derniere_sortie.wav`
- Si `nom_fichier` est renseigné, le fichier utilisé est `/tmp/<nom_fichier>.wav`
- Cette séparation permet de pré-générer les fichiers lents avec Piper, puis de rejouer rapidement les WAV en temps réel

## Construction

```bash
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

## Nettoyage ciblé

Si un fichier `.srv` est modifié ou supprimé, ROS 2 peut conserver des artefacts générés obsolètes dans `build/` et `install/`. Un simple `colcon build` ne suffit pas toujours. Dans ce cas, il faut nettoier les packages concernés puis les reconstruire. Un script existe pour ceci, procéder alors : 

```bash
./scripts/nettoyer_packages_ros.sh commun robot_devastator
source /opt/ros/jazzy/setup.bash
colcon build --packages-select commun robot_devastator
source install/setup.bash
```

Ce contournement est utile notamment après suppression ou renommage d’une interface ROS comme un `.srv`.

## Structure

- `src/` : sources du workspace
- `build/` : fichiers de compilation générés
- `install/` : artefacts d'installation
- `log/` : journaux de build
