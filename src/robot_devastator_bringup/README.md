# robot_devastator_bringup

`robot_devastator_bringup` est le point d'entrée unique pour lancer le robot Devastator. Il
centralise les fichiers de lancement et les fichiers de paramètres, ce qui évite d'avoir plusieurs
points d'entrée concurrents dans les packages applicatifs.

## Fichiers de lancement

| Fichier | Nœuds lancés | Cas d'usage |
|---|---|---|
| `devastator.launch.yaml` | `interface_pico`, `arbitre_commande_moteurs`, `annonces_audio`, `evitement_obstacle` | Lancement complet du robot en mode manuel, autonomie en attente |
| `interface_pico.launch.yaml` | `interface_pico` | Diagnostic isolé de la couche UART, encodeurs, sonar et tourelle |

## Fichiers de configuration

| Fichier | Nœud cible | Paramètres clés |
|---|---|---|
| `interface_pico.yaml` | `interface_pico` | Port UART, débit, délai d'expiration consigne moteur, périodes sonar et encodeurs |
| `arbitre_commande_moteurs.yaml` | `arbitre_commande_moteurs` | Mode initial (`manuel`), période de publication, délai d'expiration source |
| `annonces_audio.yaml` | `annonces_audio` | Exécutable Piper, modèle vocal, délai de répétition, liste des annonces par événement |
| `autonomie_simple.yaml` | `evitement_obstacle` | Distance d'arrêt, vitesses, angles de tourelle, durées de rotation et de recul |
| `teleop_clavier.yaml` | `teleop_clavier` | Vitesse initiale, bornes de vitesse, pas, période de publication |

## Lancement sur Raspberry Pi 4 via SSH

Build initial ou après modification :

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico robot_devastator robot_devastator_bringup
source install/setup.bash
```

Lancement complet du robot :

```bash
ros2 launch robot_devastator_bringup devastator.launch.yaml
```

Lancement isolé de la couche Pico (diagnostic) :

```bash
ros2 launch robot_devastator_bringup interface_pico.launch.yaml
```

## Téléopération clavier

`teleop_clavier` se lance séparément dans un terminal interactif, local ou SSH, car il capture
les touches du terminal courant :

```bash
# Terminal 1 : robot lancé
ros2 launch robot_devastator_bringup devastator.launch.yaml

# Terminal 2 : conduite clavier en avant-plan
ros2 run robot_devastator teleop_clavier --ros-args --params-file src/robot_devastator_bringup/config/teleop_clavier.yaml
```

## Tâches VSCode (Legion-Linux)

Depuis VSCode avec le profil `ROS2`, les tâches suivantes sont disponibles via
`Tasks: Run Task` (F1) :

| Tâche | Équivalent CLI |
|---|---|
| `ROS 2 - Lancer Devastator` | `ros2 launch robot_devastator_bringup devastator.launch.yaml` |
| `ROS 2 - Lancer interface Pico` | `ros2 launch robot_devastator_bringup interface_pico.launch.yaml` |
| `ROS 2 - Build Devastator` | `colcon build --symlink-install --packages-select ...` |
| `ROS 2 - Nettoyer packages Devastator` | Nettoyage ciblé de `build/` et `install/` |
