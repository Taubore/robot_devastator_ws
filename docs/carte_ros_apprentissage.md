# Carte ROS 2 pour l'apprentissage

Cette carte décrit les interfaces visibles dans le code source du workspace Devastator. Elle sert
de guide de lecture : elle ne remplace pas l'observation du graphe ROS 2 pendant l'exécution.

## Vue d'ensemble

Le flux principal de l'autonomie simple est le suivant :

```text
evitement_obstacle_node
  ├─ publie les commandes moteurs et tourelle
  ├─ reçoit la distance ultrason
  └─ publie les événements significatifs
          │
          ▼
principal ── demande la génération ou la lecture audio ──► voix_piper

interface_pico_node
  ├─ traduit les commandes ROS 2 en lignes UART vers le Pico WH
  └─ traduit les réponses UART du Pico WH en topics ROS 2
```

## Packages ROS 2

| Package | Type de build | Rôle |
|---|---|---|
| `commun` | `ament_cmake` | Définit les messages et services personnalisés partagés par les autres packages. |
| `interface_pico` | `ament_python` | Relie ROS 2 au Pico WH par UART pour les moteurs, la tourelle et la distance ultrason. |
| `robot_devastator` | `ament_python` | Contient le comportement autonome simple et les capacités audio du robot. |
| `robot_devastator_bringup` | `ament_cmake` | Assemble les nœuds et leurs fichiers de paramètres pour les lancements courants. |

### Fichiers importants par package

#### `commun`

Ce package ne contient aucun fichier Python important.

| Fichier | Rôle |
|---|---|
| `src/commun/msg/ConsigneMoteurs.msg` | Définit une consigne brute pour les moteurs gauche et droit. |
| `src/commun/srv/GenererAudio.srv` | Définit la demande de génération d'un fichier WAV à partir d'un texte. |
| `src/commun/srv/JouerAudio.srv` | Définit la demande de lecture d'un fichier WAV existant. |

#### `interface_pico`

| Fichier Python | Rôle |
|---|---|
| `src/interface_pico/interface_pico/interface_pico.py` | Définit le nœud ROS 2 `interface_pico_node`. |
| `src/interface_pico/interface_pico/transport_serie_pico.py` | Isole l'échange UART en lignes ASCII avec le Pico WH. Ce fichier ne définit pas de nœud ROS 2. |
| `src/interface_pico/setup.py` | Déclare l'exécutable ROS 2 Python `interface_pico_node`. |

#### `robot_devastator`

| Fichier Python | Rôle |
|---|---|
| `src/robot_devastator/robot_devastator/evitement_obstacle.py` | Définit la machine d'états de l'autonomie simple. |
| `src/robot_devastator/robot_devastator/principal.py` | Définit l'orchestrateur des annonces audio. |
| `src/robot_devastator/robot_devastator/voix_piper_service.py` | Définit les services de génération et de lecture audio avec Piper et `aplay`. |
| `src/robot_devastator/setup.py` | Déclare les trois exécutables ROS 2 Python du package. |

#### `robot_devastator_bringup`

Ce package ne contient aucun fichier Python important. Il centralise les fichiers YAML de lancement
et de paramètres décrits plus bas.

## Nœuds ROS 2

### `interface_pico_node`

| Élément | Valeur |
|---|---|
| Package | `interface_pico` |
| Fichier Python | `src/interface_pico/interface_pico/interface_pico.py` |
| Classe | `NoeudInterfacePico` |
| Exécutable ROS 2 | `interface_pico_node` |
| Rôle | Adapter les topics et services ROS 2 aux commandes UART comprises par le Pico WH, puis republier les réponses utiles du Pico. |

**Publishers créés**

| Topic | Type | Rôle |
|---|---|---|
| `/pico/etat` | `std_msgs/msg/String` | Publier chaque ligne texte reçue du Pico. |
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | Publier une ligne UART numérique comme distance ultrason en millimètres. |

**Subscriptions créées**

| Topic | Type | Rôle |
|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | Envoyer immédiatement au Pico une consigne moteur valide. |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Envoyer au Pico un angle de servo valide entre `0` et `180` degrés. |

**Services créés**

| Service | Type | Rôle |
|---|---|---|
| `/pico/stop` | `std_srvs/srv/Trigger` | Envoyer `STOP` au Pico et mémoriser la consigne moteur `(0, 0)`. |
| `/pico/ping` | `std_srvs/srv/Trigger` | Envoyer `PING` au Pico. Le succès confirme l'envoi UART, pas la réception d'une réponse. |

**Clients de services utilisés**

Aucun.

**Timers créés**

| Période | Callback | Rôle |
|---|---|---|
| Paramètre `timeout_lecture` | `_lire_et_traiter_reponse_uart_callback` | Lire une éventuelle ligne UART sans boucle bloquante. |
| Paramètre `periode_maintien_s` | `_maintenir_derniere_consigne_moteurs_callback` | Répéter la dernière consigne moteur valide avant le timeout du Pico. |
| Paramètre `periode_distance_s` | `_demander_distance_callback` | Envoyer périodiquement la commande UART `DIST`. |

**Paramètres déclarés et lus**

| Paramètre | Valeur par défaut dans le code | Valeur dans `config/interface_pico.yaml` | Rôle |
|---|---:|---:|---|
| `port` | `/dev/ttyS0` | `/dev/ttyS0` | Port série relié au Pico. |
| `debit` | `115200` | `115200` | Débit UART en bauds. |
| `timeout_lecture` | `0.1` | `0.02` | Durée maximale d'une lecture UART et période du timer de lecture. |
| `periode_maintien_s` | `0.1` | `0.25` | Intervalle de répétition de la dernière consigne moteur. |
| `periode_distance_s` | `0.5` | `0.10` | Intervalle entre deux demandes de distance ultrason. |

### `evitement_obstacle_node`

| Élément | Valeur |
|---|---|
| Package | `robot_devastator` |
| Fichier Python | `src/robot_devastator/robot_devastator/evitement_obstacle.py` |
| Classe | `EvitementObstacle` |
| Exécutable ROS 2 | `evitement_obstacle` |
| Rôle | Faire avancer le robot, analyser un obstacle avec la tourelle et choisir une rotation jusqu'à retrouver un passage dégagé. |

**Publishers créés**

| Topic | Type | Rôle |
|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | Commander l'avance, l'arrêt, la rotation sur place ou le recul. |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Orienter le capteur ultrason à gauche, au centre ou à droite. |
| `/robot/evenement` | `std_msgs/msg/String` | Signaler les transitions significatives pour les annonces audio. |

**Subscriptions créées**

| Topic | Type | Rôle |
|---|---|---|
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | Mémoriser la dernière mesure valide et confirmer un dégagement pendant la rotation. |

**Services créés**

Aucun.

**Clients de services utilisés**

Aucun.

**Timers créés**

| Période | Callback | Rôle |
|---|---|---|
| Paramètre `periode_publication_s` | `_publier_consigne_selon_distance` | Faire progresser la machine d'états et publier une consigne sécuritaire. |

**Paramètres déclarés et lus**

| Paramètre | Valeur par défaut dans le code | Valeur dans `config/autonomie_simple.yaml` | Rôle |
|---|---:|---:|---|
| `distance_arret_mm` | `350` | `350` | Distance minimale avant le déclenchement de l'analyse d'obstacle. |
| `vitesse_avance` | `500` | `500` | Consigne appliquée pendant l'avance. |
| `periode_publication_s` | `0.1` | `0.1` | Période de progression de la machine d'états. |
| `angle_tourelle_centre_deg` | `95` | `95` | Angle utilisé pour surveiller la direction d'avance. |
| `angle_tourelle_gauche_deg` | `45` | `45` | Angle utilisé pour mesurer le dégagement à gauche. |
| `angle_tourelle_droite_deg` | `140` | `140` | Angle utilisé pour mesurer le dégagement à droite. |
| `delai_stabilisation_tourelle_s` | `0.35` | `0.35` | Attente après un mouvement de la tourelle. |
| `distance_degagement_mm` | `600` | `600` | Distance minimale pour considérer la voie dégagée pendant une rotation. |
| `mesures_degagement_requises` | `3` | `3` | Nombre de mesures dégagées consécutives nécessaires. |
| `vitesse_rotation_recherche` | `300` | `500` | Valeur absolue des consignes opposées utilisées pour tourner sur place. |
| `vitesse_recul` | `300` | `300` | Valeur absolue de la consigne utilisée pour reculer. |
| `duree_rotation_recherche_min_s` | `0.6` | `0.6` | Durée minimale de rotation avant la validation d'un dégagement. |
| `duree_rotation_recherche_max_s` | `4.0` | `3.0` | Durée maximale de rotation avant un recul de récupération. |
| `duree_recul_s` | `0.45` | `2.0` | Durée du recul de récupération. |
| `marge_choix_direction_mm` | `120` | `120` | Écart minimal entre gauche et droite pour changer le côté choisi. |

Les valeurs `45°` et `140°` sont celles de la configuration active. Leur association physique avec
les côtés gauche et droit doit être confirmée sur le robot par un essai manuel de la tourelle.

### `principal`

| Élément | Valeur |
|---|---|
| Package | `robot_devastator` |
| Fichier Python | `src/robot_devastator/robot_devastator/principal.py` |
| Classe | `Principal` |
| Exécutable ROS 2 | `principal` |
| Rôle | Préparer les fichiers WAV manquants au démarrage et demander une annonce lors d'un événement du robot. |

**Publishers créés**

Aucun.

**Subscriptions créées**

| Topic | Type | Rôle |
|---|---|---|
| `/robot/evenement` | `std_msgs/msg/String` | Recevoir une transition du comportement autonome et choisir une variante d'annonce. |

**Services créés**

Aucun.

**Clients de services utilisés**

| Service | Type | Rôle |
|---|---|---|
| `/generer_audio` | `commun/srv/GenererAudio` | Demander la génération préalable d'un fichier WAV absent du cache. |
| `/jouer_audio` | `commun/srv/JouerAudio` | Demander la lecture asynchrone d'un fichier WAV existant. |

**Timers créés**

Aucun.

**Paramètres déclarés et lus**

| Paramètre | Valeur par défaut dans le code | Valeur dans `config/principal.yaml` | Rôle |
|---|---:|---:|---|
| `delai_min_repetition_s` | `3.0` | `3.0` | Empêcher la répétition trop rapprochée d'un même événement parlé. |
| `preparer_audio_au_demarrage` | `true` | `true` | Générer les WAV manquants lors du démarrage. |
| `jouer_annonce_demarrage` | `true` | `true` | Jouer l'annonce `demarrage` après la préparation initiale. |
| `annonces.demarrage` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `demarrage`. |
| `annonces.autonomie_demarre` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `autonomie_demarre`. |
| `annonces.obstacle_detecte` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `obstacle_detecte`. |
| `annonces.analyse_obstacle` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `analyse_obstacle`. |
| `annonces.rotation_gauche` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `rotation_gauche`. |
| `annonces.rotation_droite` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `rotation_droite`. |
| `annonces.recul_recuperation` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `recul_recuperation`. |
| `annonces.reprise_avance` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `reprise_avance`. |
| `annonces.arret_robot` | Tableau de chaînes déclaré sans valeur explicite | Configuré | Variantes possibles pour l'événement `arret_robot`. |

Le format configuré d'une variante parlée est `nom_fichier|texte`. Une chaîne vide représente une
variante silencieuse participant au tirage aléatoire.

### `voix_piper`

| Élément | Valeur |
|---|---|
| Package | `robot_devastator` |
| Fichier Python | `src/robot_devastator/robot_devastator/voix_piper_service.py` |
| Classe | `VoixPiper` |
| Exécutable ROS 2 | `voix_piper_service` |
| Rôle | Exposer la génération de fichiers WAV par Piper et leur lecture par `aplay`. |

**Publishers créés**

Aucun.

**Subscriptions créées**

Aucune.

**Services créés**

| Service | Type | Rôle |
|---|---|---|
| `/generer_audio` | `commun/srv/GenererAudio` | Générer un fichier WAV nommé ou la sortie audio par défaut. |
| `/jouer_audio` | `commun/srv/JouerAudio` | Jouer un fichier WAV nommé ou la sortie audio par défaut. |

**Clients de services utilisés**

Aucun.

**Timers créés**

Aucun.

**Paramètres déclarés et lus**

| Paramètre | Valeur par défaut dans le code | Valeur dans `config/voix_piper.yaml` | Rôle |
|---|---|---|---|
| `piper_model` | `/opt/piper/voix/fr_FR-siwis-low.onnx` | `/opt/piper/voix/fr_FR-siwis-low.onnx` | Chemin du modèle vocal Piper. |
| `piper_config` | `/opt/piper/voix/fr_FR-siwis-low.onnx.json` | `/opt/piper/voix/fr_FR-siwis-low.onnx.json` | Chemin de la configuration du modèle Piper. |
| `audio_output` | `~/.cache/robot_devastator/audio/derniere_sortie.wav` | Aucun | Fichier utilisé lorsqu'aucun nom n'est fourni dans une requête. |
| `command_timeout_s` | `15.0` | `15.0` | Durée maximale accordée à Piper et à `aplay`. |

## Topics

| Topic | Type | Producteur connu dans le workspace | Consommateur connu dans le workspace | Rôle |
|---|---|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | `evitement_obstacle_node` | `interface_pico_node` | Transmettre les consignes des moteurs gauche et droit vers le Pico. |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | `evitement_obstacle_node` | `interface_pico_node` | Commander l'angle du servo de tourelle en degrés. |
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | `interface_pico_node` | `evitement_obstacle_node` | Publier la distance ultrason en millimètres. |
| `/pico/etat` | `std_msgs/msg/String` | `interface_pico_node` | Aucun consommateur interne connu | Publier les lignes texte reçues du Pico pour le diagnostic. |
| `/robot/evenement` | `std_msgs/msg/String` | `evitement_obstacle_node` | `principal` | Diffuser les transitions significatives de l'autonomie simple. |

## Services

| Service | Type | Serveur | Client connu dans le workspace | Rôle |
|---|---|---|---|---|
| `/pico/ping` | `std_srvs/srv/Trigger` | `interface_pico_node` | Aucun client interne connu | Envoyer `PING` sur l'UART ; le succès ne confirme pas la réception d'une réponse. |
| `/pico/stop` | `std_srvs/srv/Trigger` | `interface_pico_node` | Aucun client interne connu | Demander un arrêt explicite des moteurs au Pico. |
| `/generer_audio` | `commun/srv/GenererAudio` | `voix_piper` | `principal` | Générer un fichier WAV absent du cache persistant. |
| `/jouer_audio` | `commun/srv/JouerAudio` | `voix_piper` | `principal` | Jouer un fichier WAV existant. |

## Fichiers de lancement

### `src/robot_devastator_bringup/launch/interface_pico.launch.yaml`

| Nœud lancé | Package | Exécutable | Fichier de paramètres |
|---|---|---|---|
| `interface_pico_node` | `interface_pico` | `interface_pico_node` | `src/robot_devastator_bringup/config/interface_pico.yaml` |

**Objectif :** lancer uniquement le pont UART vers le Pico afin de tester progressivement les
actionneurs, les mesures ultrason et les services de diagnostic.

### `src/robot_devastator_bringup/launch/autonomie_simple.launch.yaml`

| Nœud lancé | Package | Exécutable | Fichier de paramètres |
|---|---|---|---|
| `interface_pico_node` | `interface_pico` | `interface_pico_node` | `src/robot_devastator_bringup/config/interface_pico.yaml` |
| `voix_piper` | `robot_devastator` | `voix_piper_service` | `src/robot_devastator_bringup/config/voix_piper.yaml` |
| `principal` | `robot_devastator` | `principal` | `src/robot_devastator_bringup/config/principal.yaml` |
| `evitement_obstacle_node` | `robot_devastator` | `evitement_obstacle` | `src/robot_devastator_bringup/config/autonomie_simple.yaml` |

**Objectif :** assembler le pont Pico, l'évitement d'obstacle et les annonces audio pour obtenir
l'autonomie simple actuelle du robot.

## Interfaces personnalisées

| Interface | Champs | Rôle |
|---|---|---|
| `commun/msg/ConsigneMoteurs` | `int16 gauche`, `int16 droite` | Transporter les deux consignes moteur brutes. Le code applique la plage `-1000` à `1000`. |
| `commun/srv/GenererAudio` | Requête : `texte`, `nom_fichier`; réponse : `succes`, `message`, `chemin_fichier` | Générer un fichier WAV à partir d'un texte. |
| `commun/srv/JouerAudio` | Requête : `nom_fichier`; réponse : `succes`, `message`, `chemin_fichier` | Jouer un fichier WAV existant. |

## Points à retenir pour l'étude

- `interface_pico_node` est une couche d'adaptation matérielle. La logique de décision autonome ne
  doit pas y être cherchée.
- `evitement_obstacle_node` contient la machine d'états : c'est le fichier principal à lire pour
  comprendre les décisions du robot.
- `principal` transforme des événements de haut niveau en demandes audio ; il ne pilote pas les
  moteurs.
- `voix_piper` isole les appels aux programmes externes `piper` et `aplay`.
- Aucun serveur ou client d'action ROS 2 n'est défini dans le code actuel.

## Incertitudes et limites de cette carte

- Cette carte provient d'une analyse statique du workspace. Elle n'inventorie pas les interfaces
  ROS 2 implicites créées automatiquement par `rclpy`, comme les services de paramètres d'un nœud.
- Les outils lancés manuellement avec `ros2 topic`, `ros2 service` ou depuis un autre dépôt peuvent
  ajouter des producteurs, consommateurs ou clients qui ne sont pas visibles ici.
- Les services `generer_audio` et `jouer_audio` sont créés avec des noms relatifs dans
  `voix_piper_service.py`. Avec les lancements actuels sans namespace, ROS 2 les résout en
  `/generer_audio` et `/jouer_audio`.
- `/pico/etat` publie toutes les lignes UART reçues. Une ligne composée uniquement de chiffres est
  aussi publiée sur `/pico/distance_ultrason_mm`; la carte ne suppose pas d'autres formats de réponse
  que ceux explicitement traités dans le code.
