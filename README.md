# Devastator

Workspace ROS 2 du projet Devastator pour la cible Raspberry Pi 4.

## Environnement

- ROS 2 Jazzy
- Ubuntu 24.04
- Raspberry Pi 4

## Contenu

- `src/commun` : interfaces ROS 2
- `src/robot_devastator` : package Python principal
- `src/interface_pico` : interface ROS 2 simple entre le Raspberry Pi 4 et le Pico WH

## Services audio

- `generer_audio` : génère un fichier WAV à partir d’un texte
- `jouer_audio` : lit un fichier WAV déjà généré
- Les fichiers générés sont conservés dans `~/.cache/robot_devastator/audio`
- Si `nom_fichier` est vide, le fichier utilisé est `~/.cache/robot_devastator/audio/derniere_sortie.wav`
- Si `nom_fichier` est renseigné, le fichier utilisé est `~/.cache/robot_devastator/audio/<nom_fichier>.wav`
- Le paramètre ROS 2 `command_timeout_s` règle le délai maximal des commandes `piper` et `aplay`, par défaut `10.0`
- Cette séparation permet de pré-générer les fichiers lents avec Piper, puis de rejouer rapidement les WAV en temps réel

## Interface Pico

- Topic d’entrée `consigne_moteurs` : `commun/msg/ConsigneMoteurs`
- Topic d’entrée `commande_tourelle_deg` : `std_msgs/msg/Int32`, angle servo de tourelle
- Topic publié `distance_ultrason_mm` : `std_msgs/msg/Int32`, distance ultrason en millimètres
- Services `ping` et `stop` : `std_srvs/srv/Trigger`
- Topic d’état `etat_pico` : `std_msgs/msg/String`
- Nœud : `interface_pico_node`
- Lancement :

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select commun interface_pico
source install/setup.bash
ros2 launch interface_pico interface_pico.launch.py
```

Exemple de consigne moteur :

```bash
ros2 topic pub --once /consigne_moteurs commun/msg/ConsigneMoteurs "{gauche: 200, droite: 200}"
```

## Construction

```bash
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

## Nettoyage ciblé

Si un fichier `.srv` est modifié ou supprimé, ROS 2 peut conserver des artefacts générés obsolètes dans `build/` et `install/`. Un simple `colcon build` ne suffit pas toujours. Dans ce cas, il faut nettoyer les packages concernés puis les reconstruire. Un script existe pour ceci, procéder alors :

```bash
./scripts/nettoyer_packages_ros.sh commun robot_devastator interface_pico
source /opt/ros/jazzy/setup.bash
colcon build --packages-select commun robot_devastator interface_pico
source install/setup.bash
```

Ce contournement est utile notamment après suppression ou renommage d’une interface ROS comme un `.srv` ou un `.msg`.

## Structure

- `src/` : sources du workspace
- `build/` : fichiers de compilation générés
- `install/` : artefacts d'installation
- `log/` : journaux de build
