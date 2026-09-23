# robot_devastator_description

Description URDF/Xacro du robot (visuel, collisions, TF) et fichiers de simulation Gazebo / visualisation RViz. Aucun nœud de production : ce package fournit `robot_description` et des lancements de diagnostic/visualisation, utilisés sur Legion-Linux uniquement.

## Structure

| Dossier | Rôle |
|---|---|
| `urdf/` | Xacro du robot (`devastator.urdf.xacro` inclut `corps`, `roues`, `capteurs`, `devastator_gazebo`) |
| `launch/` | `simulation.launch.py` (robot_state_publisher + RViz pour Gazebo), `affichage.launch.py` (RViz seul, roues manuelles) |
| `config/` | Configuration RViz (`devastator.rviz`) |
| `worlds/` | Mondes SDF pour Gazebo |

## Simulation Gazebo (Legion-Linux)

Lancée par `robot_devastator_bringup/launch/diag_simulation.launch.yaml` (tâche VSCode `ROS 2 - Lancer simulation Gazebo`), jamais directement.

### Monde : `worlds/piece_test.sdf`

Pièce fermée ~4 m x 5 m avec trois obstacles asymétriques (boîte, cylindre, mur court), pour que le scan lidar ne soit jamais ambigu entre deux poses par symétrie — piège classique pour le scan matching de `slam_toolbox` (Phase 10). Emplacement choisi dans ce package plutôt qu'un nouveau package : `robot_devastator_description` est déjà propriétaire de tout ce qui concerne la simulation/visualisation du robot (voir AGENTS.md, règle anti-prolifération de packages).

### Lidar simulé (`devastator_gazebo.xacro`)

Capteur `gpu_lidar` attaché à `laser_link` (position réelle mesurée, voir `capteurs.xacro`), calqué sur le RPLIDAR A1M8 réel :

| Paramètre | Valeur | Source |
|---|---|---|
| `update_rate` | 6,8 Hz | Fréquence mesurée sur le RPLIDAR A1M8 réel — `docs/inventaire_composantes.md`, `docs/decisions_et_lecons.md` (section « Qualité du scan RPLIDAR A1M8 ») |
| `samples` (par tour) | 588 | Calculé : 4000 Hz (taux d'échantillonnage mode standard, fiche technique Slamtec LD108 A1M8, externe au dépôt) ÷ 6,8 Hz mesuré |
| `range.min` / `range.max` | 0,15 m / 12,0 m | Défauts du pilote officiel `rplidar_ros` pour l'A1M8 — **non mesurés sur ce robot**, non documentés ailleurs dans ce dépôt |

`<gz_frame_id>laser_link</gz_frame_id>` force le `frame_id` publié dans `/scan` à `laser_link` : sans cette balise, Gazebo Harmonic (gz-sim 8) publie par défaut un nom composé selon la hiérarchie de liens (ex. `devastator/base_link/laser_link`), pas le nom du lien seul.

Toutes les balises `<gazebo>` ajoutées sont ignorées par le robot réel, qui charge le même `devastator.urdf.xacro` via `robot_state_publisher` (elles n'ont d'effet que sous Gazebo).

### Horloge simulée

`/clock` est ponté (voir `robot_devastator_bringup/config/gazebo_bridge.yaml`) et `use_sim_time` est actif sur `robot_state_publisher` et `rviz2` (`simulation.launch.py`) — prérequis strict de `slam_toolbox`.

## Test

```bash
ros2 launch robot_devastator_bringup diag_simulation.launch.yaml
```

Dans RViz (Fixed Frame `map` par défaut depuis l'ajout de `slam_toolbox`, passer à `odom` pour vérifier l'odométrie seule) : le scan doit dessiner les murs et les obstacles, rester aligné pendant une rotation sur place (`teleop_twist_keyboard`), et `ros2 topic hz /scan` doit indiquer ~6,8 Hz.

## SLAM (Phase 10)

`diag_simulation.launch.yaml` inclut `online_async_launch.py` de `slam_toolbox` (`sudo apt install ros-jazzy-slam-toolbox`) avec `config/slam_toolbox.yaml` du package bringup. Repères confirmés en simulation : `odom → base_footprint` vient de Gazebo (DiffDrive), le reste de l'arbre de `robot_state_publisher`, et `slam_toolbox` publie `map → odom`. Le repère de base est `base_footprint`, pas `base_link`. RViz affiche `/map` (durabilité Transient Local). Pas de sauvegarde de carte à cette étape.

Test : lancer la simulation, conduire avec `ros2 run teleop_twist_keyboard teleop_twist_keyboard` à basse vitesse. `ros2 lifecycle get /slam_toolbox` doit répondre `active`. La carte apparaît après le premier déplacement de 0,5 m ou rotation de 0,5 rad, et dessine les murs et les trois obstacles sans dupliquer ni dériver au retour sur place.

## Limites connues

- Portée du lidar simulé non validée contre une mesure réelle (voir tableau ci-dessus).
- Aucun bruit de mesure calqué sur le comportement réel (trous environnementaux documentés dans `docs/decisions_et_lecons.md`) : seul un bruit gaussien générique est appliqué.
