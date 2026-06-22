# robot_devastator

`robot_devastator` est le package ROS 2 Python qui contient la logique applicative du robot
Devastator : conduite manuelle, arbitrage des commandes moteurs, comportement d'évitement
d'obstacle et annonces audio.

## Nœuds

| Nœud | Exécutable | État | Rôle |
|---|---|---|---|
| `arbitre_commande_moteurs` | `arbitre_commande_moteurs` | Actif | Sélectionner une seule source moteur active et la relayer vers `/pico/commande_moteurs` |
| `annonces_audio` | `annonces_audio` | Actif | Préparer les WAV avec Piper et jouer les annonces selon les événements du robot |
| `teleop_clavier` | `teleop_clavier` | Actif | Conduire le robot au clavier et basculer entre mode manuel et autonomie |
| `evitement_obstacle` | `evitement_obstacle` | Expérimental | Avancer, détecter un obstacle, balayer la tourelle et tourner vers le dégagement |

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

### `teleop_clavier`

| Direction | Topic | Type | Rôle |
|---|---|---|---|
| Sortie | `/robot/commande_moteurs/manuelle` | `commun/msg/ConsigneMoteurs` | Consignes clavier vers l'arbitre |
| Sortie | `/robot/mode_conduite` | `std_msgs/msg/String` | Bascule `manuel` / `autonomie` |

### `evitement_obstacle`

| Direction | Topic | Type | Rôle |
|---|---|---|---|
| Entrée | `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | Distance ultrason en millimètres |
| Sortie | `/robot/commande_moteurs/autonomie` | `commun/msg/ConsigneMoteurs` | Consignes moteur de l'autonomie |
| Sortie | `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Angle servo de tourelle en degrés |
| Sortie | `/robot/evenement` | `std_msgs/msg/String` | Transitions significatives du comportement |

## Paramètres YAML importants

### `arbitre_commande_moteurs` — `config/arbitre_commande_moteurs.yaml`

| Paramètre | Valeur par défaut | Effet |
|---|---|---|
| `mode_initial` | `manuel` | Source active au démarrage ; le clavier garde la main |
| `periode_publication_s` | `0.1` | Intervalle de publication vers `/pico/commande_moteurs` |
| `delai_expiration_source_s` | `0.35` | Délai sans commande de la source active avant arrêt forcé |

### `annonces_audio` — `config/annonces_audio.yaml`

| Paramètre | Valeur par défaut | Effet |
|---|---|---|
| `delai_min_repetition_s` | `3.0` | Empêche une même annonce de se répéter trop rapidement |
| `preparer_audio_au_demarrage` | `true` | Génère les WAV manquants avec Piper avant d'écouter les événements |
| `jouer_annonce_demarrage` | `true` | Joue une annonce après la préparation initiale |
| `piper_executable` | `/usr/local/bin/piper` | Chemin de l'exécutable Piper sur le Raspberry Pi 4 |
| `piper_model` | `/opt/piper/voix/fr_FR-siwis-low.onnx` | Modèle vocal français utilisé pour la synthèse |
| `command_timeout_s` | `15.0` | Durée maximale accordée à Piper et à `aplay` avant échec |

Les annonces sont définies par événement dans `annonces.yaml` sous la clé `annonces.<evenement>`.
Chaque entrée est une liste de variantes ; une chaîne vide représente une variante silencieuse
choisie aléatoirement.

### `teleop_clavier` — `config/teleop_clavier.yaml`

| Paramètre | Valeur par défaut | Effet |
|---|---|---|
| `vitesse_initiale` | `300` | Vitesse appliquée au démarrage |
| `vitesse_min` | `300` | Borne basse de vitesse ajustable au clavier |
| `vitesse_max` | `1000` | Borne haute de vitesse ajustable au clavier |
| `pas_vitesse` | `50` | Incrément appliqué par `=` et `-` |
| `periode_publication_s` | `0.1` | Période de lecture clavier et de publication |

Touches disponibles : `w` avance, `s` recule, `a` tourne à gauche, `d` tourne à droite,
`espace` arrête, `=` augmente la vitesse, `-` diminue la vitesse, `m` bascule entre
`manuel` et `autonomie`, `x` quitte. À la sortie normale ou avec `Ctrl+C`, un arrêt moteur
explicite est publié.

### `evitement_obstacle` — `config/autonomie_simple.yaml`

| Paramètre | Valeur par défaut | Effet |
|---|---|---|
| `actif_au_demarrage` | `false` | Démarre en attente ; attend la bascule `m` du clavier |
| `distance_arret_mm` | `350` | Distance avant déclenchant l'arrêt et le balayage |
| `vitesse_avance` | `500` | Consigne moteur pendant l'avance lente |
| `distance_degagement_mm` | `600` | Distance requise pour considérer une voie dégagée |
| `mesures_degagement_requises` | `3` | Mesures dégagées consécutives avant d'arrêter la rotation |
| `duree_rotation_recherche_max_s` | `3.0` | Durée maximale de recherche avant recul |
| `duree_recul_s` | `2.0` | Durée du recul de récupération |

## Notes

**`teleop_clavier`** doit être lancé séparément dans un terminal interactif, local ou via SSH,
car il capture les touches du terminal courant. Il ne peut pas s'exécuter en arrière-plan.

**`evitement_obstacle`** est expérimental. Il démarre systématiquement en attente
(`actif_au_demarrage: false`) et ne devient actif que lorsque `teleop_clavier` bascule en mode
autonomie avec la touche `m`.
