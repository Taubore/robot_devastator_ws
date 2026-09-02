# robot_devastator_bringup

`robot_devastator_bringup` est le point d'entrée unique pour lancer le robot Devastator. Il
centralise les fichiers de lancement et les fichiers de paramètres, ce qui évite d'avoir plusieurs
points d'entrée concurrents dans les packages applicatifs.

## Principe des fichiers de lancement

Le lancement primaire `devastator.launch.yaml` démarre tous les nœuds de production. Seul
`teleop.launch.yaml` fait exception au regroupement, car `teleop_clavier` capture les touches du
terminal courant et ne peut pas tourner en arrière-plan. Tous les autres fichiers sont des
lancements de diagnostic, préfixés `diag_`, jamais utilisés en exploitation normale.

Démarrer le robot avec téléopération tient en deux commandes, dans deux terminaux :

```bash
ros2 launch robot_devastator_bringup devastator.launch.yaml
ros2 launch robot_devastator_bringup teleop.launch.yaml
```

## Fichiers de lancement

| Fichier | Nœuds lancés | Cas d'usage |
|---|---|---|
| `devastator.launch.yaml` | `surveillance_alimentation`, `interface_pico`, `odometrie`, `arbitre_commande_moteurs`, `annonces_audio`, `evitement_obstacle` | Lancement complet du robot en mode manuel, autonomie en attente |
| `teleop.launch.yaml` | `teleop_clavier` | Téléopération clavier, dans un terminal interactif séparé (production, exception documentée) |
| `diag_interface_pico.launch.yaml` | `interface_pico` | Diagnostic isolé de la couche UART, encodeurs, sonar et tourelle |
| `diag_surveillance_alimentation.launch.yaml` | `surveillance_alimentation` | Isole le sous-système INA260 pour une mise au point (le nœud tourne en production dans `devastator.launch.yaml`) |
| `diag_simulation.launch.yaml` | Simulation Gazebo | Diagnostic visuel sur Legion-Linux, sans matériel |

## Fichiers de configuration

| Fichier | Nœud cible | Paramètres clés |
|---|---|---|
| `interface_pico.yaml` | `interface_pico` | Port UART, débit, délai d'expiration consigne moteur, périodes sonar et encodeurs |
| `mecanique.yaml` | `odometrie` | Ticks par tour, ticks par mètre gauche/droite/moyen, entraxe — mesurés en Phase 3 |
| `arbitre_commande_moteurs.yaml` | `arbitre_commande_moteurs` | Mode initial (`manuel`), période de publication, délai d'expiration source |
| `annonces_audio.yaml` | `annonces_audio` | Exécutable Piper, modèle vocal, délai de répétition, liste des annonces par événement |
| `autonomie_simple.yaml` | `evitement_obstacle` | Distance d'arrêt, vitesses, angles de tourelle, durées de rotation et de recul |
| `teleop_clavier.yaml` | `teleop_clavier` | Vitesse initiale, bornes de vitesse, pas, période de publication |
| `surveillance_alimentation.yaml` | `surveillance_alimentation` | Bus I2C, adresses INA260, seuils de tension par rail, porte de courant, temporisation, libellés d'événement |

## Lancement sur Raspberry Pi 4 via SSH

Build initial ou après modification :

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico odometrie robot_devastator surveillance_alimentation robot_devastator_bringup
source install/setup.bash
```

Lancement complet du robot (téléopération incluse), dans deux terminaux SSH :

```bash
# Terminal 1 : robot complet, mode manuel, autonomie et odométrie en marche
ros2 launch robot_devastator_bringup devastator.launch.yaml

# Terminal 2 : conduite clavier en avant-plan
ros2 launch robot_devastator_bringup teleop.launch.yaml
```

Lancement isolé de la couche Pico (diagnostic) :

```bash
ros2 launch robot_devastator_bringup diag_interface_pico.launch.yaml
```

## Téléopération clavier

`teleop.launch.yaml` se lance dans un terminal interactif, local ou SSH, en plus de
`devastator.launch.yaml` : `teleop_clavier` capture les touches du terminal courant et ne peut
pas tourner en arrière-plan. C'est l'exception documentée au principe du lancement primaire
unique. Le launch charge `config/teleop_clavier.yaml`, ce qui évite la commande `ros2 run` longue
et dépendante du répertoire courant.

## Tâches VSCode (Legion-Linux)

L'exécution des nœuds se fait toujours en terminal, sur le Raspberry Pi 4. Les tâches VSCode ne
couvrent que le build, le nettoyage et la simulation Gazebo sans matériel. Elles sont disponibles
via `Tasks: Run Task` (F1) avec le profil `ROS2` :

| Tâche | Équivalent CLI |
|---|---|
| `ROS 2 - Build Devastator` | `colcon build --symlink-install --packages-select ...` |
| `ROS 2 - Build complet` | `colcon build --symlink-install` |
| `ROS 2 - Nettoyer packages Devastator` | Nettoyage ciblé de `build/` et `install/` |
| `ROS 2 - Nettoyer workspace complet` | Nettoyage complet de `build/`, `install/` et `log/` |
| `ROS 2 - Lancer simulation Gazebo` | `ros2 launch robot_devastator_bringup diag_simulation.launch.yaml` |
