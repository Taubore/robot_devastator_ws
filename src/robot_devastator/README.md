# robot_devastator

`robot_devastator` est le package ROS 2 Python qui contient la logique applicative du robot Devastator : conduite manuelle, arbitrage des commandes moteurs, comportement d'évitement d'obstacle, annonces audio et gestion du RPLIDAR.

## Nœuds

| Nœud | Exécutable | État | Rôle |
|---|---|---|---|
| `arbitre_commande_moteurs` | `arbitre_commande_moteurs` | Actif | Sélectionner une seule source moteur active et la relayer vers `/pico/commande_moteurs` |
| `annonces_audio` | `annonces_audio` | Actif | Préparer les WAV avec Piper et jouer les annonces selon les événements du robot |
| `teleop_clavier` | `teleop_clavier` | Actif | Conduire le robot au clavier et basculer entre mode manuel et autonomie |
| `evitement_obstacle` | `evitement_obstacle` | Expérimental | Avancer, détecter un obstacle, balayer la tourelle et tourner vers le dégagement |
| `gestion_lidar` | `gestion_lidar` | Actif | Pont vers `rplidar_composition` : centralise l'état veille/actif du RPLIDAR pour toutes les sources |

## Interfaces ROS 2

### `arbitre_commande_moteurs`

| Direction | Topic | Type | Rôle |
|---|---|---|---|
| Entrée | `/robot/commande_moteurs/manuelle` | `commun/msg/ConsigneMoteurs` | Consignes issues du clavier |
| Entrée | `/robot/commande_moteurs/autonomie` | `commun/msg/ConsigneMoteurs` | Consignes issues de l'autonomie |
| Entrée | `/robot/mode_conduite` | `std_msgs/msg/String` | Source active : `manuel` ou `autonomie` |
| Sortie | `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | Commande moteur transmise à `interface_pico` |

### `annonces_audio`

| Direction | Topic | Type | Rôle |
|---|---|---|---|
| Entrée | `/robot/evenement` | `std_msgs/msg/String` | Événement déclenchant une annonce |
| Sortie | `/robot/parole_en_cours` | `std_msgs/msg/Bool` | `true` pendant la lecture `aplay`, `false` sinon (QoS transient local, profondeur 1) |

### `teleop_clavier`

| Direction | Topic | Type | Rôle |
|---|---|---|---|
| Sortie | `/robot/commande_moteurs/manuelle` | `commun/msg/ConsigneMoteurs` | Consignes clavier vers l'arbitre |
| Sortie | `/robot/mode_conduite` | `std_msgs/msg/String` | Bascule `manuel` / `autonomie` |
| Sortie | `/affichage/page_suivante` | `std_msgs/msg/Empty` | Demande de changement de page pour un futur nœud d'affichage LCD |

### `evitement_obstacle`

| Direction | Topic | Type | Rôle |
|---|---|---|---|
| Entrée | `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | Distance ultrason en millimètres |
| Sortie | `/robot/commande_moteurs/autonomie` | `commun/msg/ConsigneMoteurs` | Consignes moteur de l'autonomie |
| Sortie | `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Angle servo de tourelle en degrés |
| Sortie | `/robot/evenement` | `std_msgs/msg/String` | Transitions significatives du comportement |

### `gestion_lidar`

| Type | Service | Interface | Rôle |
|---|---|---|---|
| Service exposé | `/activer_lidar` | `std_srvs/srv/Trigger` | Démarre le RPLIDAR (`/start_motor`) et marque `lidar_actif = true` |
| Service exposé | `/desactiver_lidar` | `std_srvs/srv/Trigger` | Arrête le RPLIDAR (`/stop_motor`) et marque `lidar_actif = false` |
| Service client | `/start_motor` | `std_srvs/srv/Empty` | Fourni par `rplidar_composition` (paquet externe, non modifié) |
| Service client | `/stop_motor` | `std_srvs/srv/Empty` | Fourni par `rplidar_composition` (paquet externe, non modifié) |

`lidar_actif` (bool, interne) est initialisé à `false`. Au démarrage, `gestion_lidar` appelle `/stop_motor` une fois pour forcer la dormance, quel que soit l'état initial du driver `rplidar_composition` (qui démarre son moteur lui-même en fin d'initialisation, bien avant que ce nœud Python soit prêt).

À la fermeture, `gestion_lidar` ne tente **aucun** arrêt du RPLIDAR. **Limite connue, mesurée** : sur le A1, le moteur est commandé par la ligne DTR de l'adaptateur USB-série, que Linux relâche dès que `rplidar_composition` ferme le port en quittant — le moteur repart alors quoi qu'il arrive. Un `/stop_motor` final serait donc annulé par cette fermeture et ne produirait qu'un log faussement rassurant. Seule une coupure d'alimentation (relais) arrêterait réellement le RPLIDAR après la fin du lancement. Voir `docs/decisions_et_lecons.md`.

`gestion_lidar` est la seule source de vérité de l'état du RPLIDAR. Toute source de commande (actuellement `teleop_clavier` en mode manuel, éventuellement un mode automatique ou Nav2 plus tard) doit passer par `/activer_lidar` et `/desactiver_lidar` plutôt que d'appeler `rplidar_composition` directement.

## Paramètres YAML importants

### `arbitre_commande_moteurs` — `config/arbitre_commande_moteurs.yaml`

Paramètres ajustables (mode initial, période de publication vers `/pico/commande_moteurs`, délai d'expiration de la source active) et leur effet : voir ce fichier YAML.

### `annonces_audio` — `config/annonces_audio.yaml`

Paramètres ajustables (délai minimal de répétition, préparation Piper au démarrage, annonce de démarrage, chemins Piper, timeout des commandes) et leur effet : voir ce fichier YAML.

Les annonces sont définies par événement dans `annonces_audio.yaml` sous la clé `annonces.<evenement>`. Chaque entrée est une liste de variantes ; une chaîne vide représente une variante silencieuse choisie aléatoirement.

Événements actuellement annoncés :

- démarrage du nœud : `demarrage` (joué directement par `annonces_audio`) ;
- comportement d'autonomie (`evitement_obstacle`) : `autonomie_demarre`, `obstacle_detecte`, `analyse_obstacle`, `rotation_gauche`, `rotation_droite`, `recul_recuperation`, `reprise_avance` ;
- alertes batterie (`surveillance_alimentation`) : `batterie_logique_faible`, `batterie_logique_critique`, `batterie_moteur_faible`, `batterie_moteur_critique`. Ces quatre événements n'ont aucune variante silencieuse : une alerte batterie est toujours prononcée.

`arret_robot` est défini mais aucun nœud ne le publie encore.

### `teleop_clavier` — `config/teleop_clavier.yaml`

Paramètres ajustables (vitesse initiale, bornes et pas de vitesse, période de publication) et leur effet : voir ce fichier YAML.

Touches disponibles : `w` avance, `s` recule, `a` tourne à gauche, `d` tourne à droite, `espace` arrête, `=` augmente la vitesse, `-` diminue la vitesse, `m` bascule entre `manuel` et `autonomie`, `p` demande la page suivante à l'affichage (actif quel que soit le mode, même sans nœud d'affichage démarré), `l` bascule le RPLIDAR entre veille et fonctionnement en appelant `/activer_lidar` ou `/desactiver_lidar` de `gestion_lidar` (mode manuel seulement, sans effet en autonomie), `x` quitte. À la sortie normale ou avec `Ctrl+C`, un arrêt moteur explicite est publié.

`teleop_clavier` ne garde qu'un état local minimal (`lidar_actif`) pour savoir quel service appeler ensuite ; `gestion_lidar` reste la seule source de vérité de l'état réel du RPLIDAR (voir sa section ci-dessus). Le RPLIDAR démarre en dormance : `/scan` ne publie rien tant que `l` n'a pas été utilisé en mode manuel.

### `evitement_obstacle` — `config/autonomie_simple.yaml`

Paramètres ajustables (activation au démarrage, distances de déclenchement et de dégagement, vitesses, durées de rotation et de recul) et leur effet : voir ce fichier YAML.

### `gestion_lidar`

Aucun paramètre YAML : les noms de service (`/activer_lidar`, `/desactiver_lidar`, `/start_motor`, `/stop_motor`) sont des invariants d'interface, pas des réglages, et rien d'autre n'est configurable. Même exception que `rplidar_composition` (voir le `README.md` de `robot_devastator_bringup`).

## Notes

**`teleop_clavier`** doit être lancé séparément dans un terminal interactif, local ou via SSH, car il capture les touches du terminal courant. Il ne peut pas s'exécuter en arrière-plan.

**`evitement_obstacle`** est expérimental. Il démarre systématiquement en attente (`actif_au_demarrage: false`) et ne devient actif que lorsque `teleop_clavier` bascule en mode autonomie avec la touche `m`.

**`/robot/parole_en_cours`** sert de signal d'état pour un futur nœud d'affichage LCD (animation de bouche). Test rapide sur le Raspberry Pi 4 : lancer `annonces_audio` isolément, observer `ros2 topic echo /robot/parole_en_cours` pendant qu'une annonce est déclenchée via `/robot/evenement`, et confirmer que le signal passe à `true` juste avant la lecture puis revient à `false` juste après. Une variante silencieuse ne doit déclencher aucune publication, puisque `aplay` n'est jamais appelé dans ce cas.

**`gestion_lidar`** : test sur le Raspberry Pi 4 avec le robot complet lancé (`devastator.launch.yaml` puis `teleop.launch.yaml`) — `ros2 topic hz /scan` ne doit rien afficher au démarrage malgré le démarrage automatique du moteur par `rplidar_composition` (dormance forcée) ; appuyer sur `l` dans `teleop_clavier` doit faire apparaître une fréquence sur `/scan` ; réappuyer sur `l` doit l'arrêter ; après `Ctrl+C` sur `devastator.launch.yaml`, le moteur du RPLIDAR se remet à tourner : limite matérielle connue et documentée (voir section `gestion_lidar` ci-dessus), pas un défaut de ce nœud, et rien n'est tenté pour la contourner.
