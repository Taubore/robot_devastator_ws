# Devastator

## Objectif du projet

Devastator est un robot mobile utilisé comme plateforme d'apprentissage pour ROS 2,
l'électronique, Python et les systèmes embarqués. Le workspace contient la logique ROS 2
exécutée sur Raspberry Pi 4, l'interface avec un Raspberry Pi Pico WH et les interfaces
communes du projet.

## Environnement

- ROS 2 Jazzy
- Ubuntu 24.04
- Raspberry Pi 4
- Raspberry Pi Pico WH
- VSCode
- Validation matérielle sur Raspberry Pi 4

## Structure du workspace

| Chemin | Rôle |
|---|---|
| `src/commun` | Interfaces ROS 2 communes |
| `src/interface_pico` | Pont ROS 2 ↔ UART ↔ Pico WH |
| `src/robot_devastator` | Logique principale du robot |
| `src/robot_devastator_bringup` | Assemblage des nœuds et paramètres de lancement |
| `docs` | Documentation du projet |
| `.vscode/tasks.json` | Tâches de build, de nettoyage et de lancement |
| `.vscode/launch.json` | Debug direct de nœuds Python précis |

## Interfaces ROS 2

### Topics

| Topic | Type | Producteur | Consommateur | Rôle |
|---|---|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | `evitement_obstacle` | `interface_pico` | Envoyer les consignes des moteurs gauche et droit vers le Pico |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Outil de test ou `evitement_obstacle` | `interface_pico` | Commander l'angle du servo de tourelle en degrés |
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | `interface_pico` | `evitement_obstacle` | Publier la distance ultrason mesurée en millimètres |
| `/pico/etat` | `std_msgs/msg/String` | `interface_pico` | Outil de diagnostic | Publier les lignes d'état reçues côté Pico |
| `/robot/evenement` | `std_msgs/msg/String` | `evitement_obstacle` | `annonces_audio` | Signaler uniquement les transitions significatives du comportement autonome |

### Services

| Service | Type | Serveur | Client connu | Rôle |
|---|---|---|---|---|
| `/pico/ping` | `std_srvs/srv/Trigger` | `interface_pico` | Outil de diagnostic | Demander l'envoi de `PING` au Pico ; le succès confirme l'envoi UART, pas la réception d'une réponse |
| `/pico/stop` | `std_srvs/srv/Trigger` | `interface_pico` | Outil de diagnostic | Demander un arrêt explicite au Pico |
| `/generer_audio` | `commun/srv/GenererAudio` | `voix_piper` | `annonces_audio` | Générer à l'avance un fichier WAV absent du cache persistant |
| `/jouer_audio` | `commun/srv/JouerAudio` | `voix_piper` | `annonces_audio` | Jouer un fichier WAV déjà généré |

### Actions

Aucune action ROS 2 n'est implémentée actuellement.

## Nœuds ROS 2

Convention retenue : les noms de nœuds et d'exécutables sont en `snake_case`, sans suffixe
technique `_node` systématique. Les clés racines des fichiers YAML de paramètres reprennent le
nom exact du nœud lancé.

| Nœud | Package | Exécutable / module | État | Rôle |
|---|---|---|---|---|
| `interface_pico` | `interface_pico` | `interface_pico` / `interface_pico.interface_pico` | Actif | Exposer les topics et services Pico, puis traduire les commandes ROS 2 vers UART |
| `evitement_obstacle` | `robot_devastator` | `evitement_obstacle` / `robot_devastator.evitement_obstacle` | Expérimental | Avancer lentement, balayer avec la tourelle, puis tourner jusqu'à trouver un dégagement |
| `annonces_audio` | `robot_devastator` | `annonces_audio` / `robot_devastator.annonces_audio` | Actif | Préparer les annonces audio et demander leur lecture selon les événements du robot |
| `voix_piper` | `robot_devastator` | `voix_piper` / `robot_devastator.voix_piper` | Actif | Générer et jouer les fichiers WAV persistants avec Piper |

## Interfaces personnalisées

| Interface | Type | Rôle |
|---|---|---|
| `commun/msg/ConsigneMoteurs` | Message | Transporter les consignes moteur gauche et droite, sur une plage prévue de `-1000` à `1000` |
| `commun/srv/GenererAudio` | Service | Demander la génération d'un fichier audio à partir d'un texte |
| `commun/srv/JouerAudio` | Service | Demander la lecture d'un fichier audio existant |

## Utilisation avec VSCode (via Quick Access - F1)

### Build

Les tâches disponibles sont définies dans `.vscode/tasks.json`.

- `Tasks: Run Build Task > ROS 2 - Build Devastator`
- `Tasks: Run Task > ROS 2 - Build complet`

### Nettoyage ciblé

- `Tasks: Run Task > ROS 2 - Nettoyer packages Devastator`

Utiliser ce nettoyage après modification, suppression ou renommage d'un `.msg` ou `.srv`, ou si
ROS 2 semble conserver des artefacts obsolètes dans `build/` ou `install/`.

### Lancement / debug

Les assemblages ROS 2 sont centralisés dans `robot_devastator_bringup`. Utiliser les tâches
VSCode suivantes selon le besoin :

- `Tasks: Run Task > ROS 2 - Lancer interface Pico`
- `Tasks: Run Task > ROS 2 - Lancer autonomie simple`

Les configurations de `.vscode/launch.json` servent seulement au debug direct d'un nœud Python
précis avec F5 :

`Nœud Python ROS 2` demande le module Python à exécuter, par exemple
`robot_devastator.evitement_obstacle`, `robot_devastator.annonces_audio` ou
`interface_pico.interface_pico`.

L'autonomie simple fait avancer lentement le robot lorsque la distance ultrason est suffisante.
Devant un obstacle, elle arrête les moteurs, oriente la tourelle à gauche, au centre puis à droite,
et compare les mesures fraîches. Elle tourne vers le côté le plus dégagé jusqu'à confirmer le
dégagement avant avec plusieurs mesures consécutives prises par le sonar recentré, après une durée
minimale de rotation. Si aucun dégagement n'est trouvé dans le délai prévu, elle recule brièvement
et refait un balayage. Elle reprend l'avance seulement si une nouvelle mesure avant est valide et
dégagée.

Par sécurité, `interface_pico` maintient une consigne moteur seulement pendant un délai borné.
Sans nouvelle consigne ROS pendant `0.5 s`, ou après une erreur UART, il transmet et mémorise un
arrêt. Une reconnexion UART repart également à l'arrêt avant d'accepter une nouvelle commande.

Au lancement de l'autonomie simple, `annonces_audio` demande à `voix_piper` de préparer les annonces
configurées. `voix_piper` génère uniquement les fichiers WAV manquants, les conserve dans
`~/.cache/robot_devastator/audio`, puis les réutilise aux lancements suivants afin de ne pas ralentir
le comportement du robot sur Raspberry Pi 4. Les annonces peuvent proposer plusieurs variantes ;
une chaîne vide dans `config/annonces_audio.yaml` représente une variante silencieuse.

## Commandes CLI de secours

Ces commandes restent utiles pour un diagnostic rapide hors VSCode.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico robot_devastator robot_devastator_bringup
source install/setup.bash
```

```bash
ros2 launch robot_devastator_bringup interface_pico.launch.yaml
ros2 launch robot_devastator_bringup autonomie_simple.launch.yaml
```

```bash
# Roues dans le vide : essai bref à faible vitesse, suivi d'un arrêt explicite attendu.
ros2 run interface_pico essai_moteurs_borne
ros2 service call /pico/ping std_srvs/srv/Trigger
ros2 service call /pico/stop std_srvs/srv/Trigger
```

## Documentation détaillée

- [Carte ROS 2 pour l'apprentissage](docs/carte_ros_apprentissage.md)
- [Journal des essais](docs/journal_essais.md)
- [Architecture cible](docs/architecture_cible.md)
- [Paramètres techniques](docs/parametres.md)
- [Connexions des composantes matérielles](docs/connexions.md)
- [Inventaire des composantes matérielles principales](docs/inventaire_composantes.md)
