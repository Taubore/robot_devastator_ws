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
| `src/odometrie` | Calcul de l'odométrie à partir des ticks encodeurs (Phase 6) |
| `src/robot_devastator` | Logique principale du robot |
| `src/robot_devastator_bringup` | Assemblage des nœuds et paramètres de lancement |
| `src/robot_devastator_description` | Description URDF/Xacro du robot et visualisation RViz |
| `docs` | Documentation du projet |
| `.vscode/tasks.json` | Tâches de build, de nettoyage et de simulation Gazebo |
| `.vscode/launch.json` | Debug direct de nœuds Python précis |

## Matériel — alimentation et procédures physiques

### Fin de séance (quotidien)

- **Débrancher le connecteur XT30 de la batterie moteur (6 V Melasta).** Le MDD3A reste alimenté en continu tant que ce connecteur est branché (buck-boost interne + LED de statut toujours actifs), même moteurs à l'arrêt. Consommation mesurée : ~32,5 mA en continu, soit ~780 mAh/jour sur un pack de 2000 mAh — à plat en environ 2,5 jours. Risque réel : inversion de cellule sur un pack NiMH 5S vidé à zéro, dommage permanent.
- Le connecteur XT30 de la batterie logique (7,2 V Tenergy) n'a **pas** besoin d'être débranché quotidiennement. Consommation de veille des deux régulateurs Pololu (EN au repos) : de l'ordre de 0,2 mA, négligeable devant l'autodécharge normale du pack. Le débrancher seulement en cas d'inactivité prévue de plusieurs jours.

### Repères de mesure (INA260, robot au repos, sans charge)

| Rail | Tension typique | Courant typique |
|---|---|---|
| Logique (7,2 V) | ~7,1–7,2 V | ~380 mA (Pi 4 sans écran HDMI) |
| Moteur (6 V) | ~5,8–6,4 V | ~20–34 mA (MDD3A en veille) |

Le courant logique varie selon la charge active (SSH, nœuds ROS 2 lancés, écran HDMI branché — ce dernier ajoute ~145 mA). Ne pas s'en servir comme seuil d'alerte batterie faible ; utiliser la tension.

### Limite de conception — lecture batterie robot éteint

Les deux INA260 sont alimentés par le rail logique 3,3 V (Pololu 4090), lui-même coupé quand l'interrupteur logique est à off. Conséquence : aucune lecture de tension ou courant batterie n'est possible robot éteint, ni via les INA260 ni via un afficheur permanent (les voltmètres LED d'origine ont été retirés). Pour vérifier l'état de charge avant un rangement prolongé, allumer le robot brièvement ou utiliser un multimètre externe.


## Interfaces ROS 2

### Topics

| Topic | Type | Producteur | Consommateur | Rôle |
|---|---|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | `arbitre_commande_moteurs` | `interface_pico` | Envoyer la commande moteur active vers le Pico |
| `/robot/commande_moteurs/manuelle` | `commun/msg/ConsigneMoteurs` | `teleop_clavier` | `arbitre_commande_moteurs` | Porter les consignes issues du clavier |
| `/robot/commande_moteurs/autonomie` | `commun/msg/ConsigneMoteurs` | `evitement_obstacle` | `arbitre_commande_moteurs` | Porter les consignes issues de l'autonomie simple |
| `/robot/mode_conduite` | `std_msgs/msg/String` | `teleop_clavier` | `arbitre_commande_moteurs` | Choisir `manuel` ou `autonomie` comme source moteur active |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Outil de test ou `evitement_obstacle` | `interface_pico` | Commander l'angle du servo de tourelle en degrés |
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | `interface_pico` | `evitement_obstacle` | Publier la distance ultrason mesurée en millimètres |
| `/pico/encodeurs` | `commun/msg/EtatEncodeurs` | `interface_pico` | `odometrie`, outil de diagnostic | Publier les ticks des encodeurs gauche et droit lus sur le Pico |
| `/pico/etat` | `std_msgs/msg/String` | `interface_pico` | Outil de diagnostic | Publier les lignes d'état reçues côté Pico |
| `/robot/evenement` | `std_msgs/msg/String` | `evitement_obstacle` | `annonces_audio` | Signaler uniquement les transitions significatives du comportement autonome |
| `/odom` | `nav_msgs/msg/Odometry` | `odometrie` | RViz, outil de diagnostic | Publier la pose et la vitesse estimées à partir des encodeurs |

### Services

| Service | Type | Serveur | Client connu | Rôle |
|---|---|---|---|---|
| `/pico/ping` | `std_srvs/srv/Trigger` | `interface_pico` | Outil de diagnostic | Envoyer `PING` et réussir seulement si le Pico répond `OK PING` dans le délai |
| `/pico/stop_moteurs` | `std_srvs/srv/Trigger` | `interface_pico` | Outil de diagnostic | Demander un arrêt explicite des moteurs au Pico avec `STOP_MOT` |
| `/pico/reset_encodeurs` | `std_srvs/srv/Trigger` | `interface_pico` | Outil de diagnostic | Remettre à zéro les compteurs d'encodeurs avec `RESET_ENC` |
| `/odometrie/reset` | `std_srvs/srv/Trigger` | `odometrie` | Outil de diagnostic | Remettre x, y, theta à zéro sans toucher aux ticks du Pico |

### Actions

Aucune action ROS 2 n'est implémentée actuellement.

## Nœuds ROS 2

Convention retenue : les noms de nœuds et d'exécutables sont en `snake_case`, sans suffixe
technique `_node` systématique. Les clés racines des fichiers YAML de paramètres reprennent le
nom exact du nœud lancé.

| Nœud | Package | Exécutable / module | État | Rôle |
|---|---|---|---|---|
| `interface_pico` | `interface_pico` | `interface_pico` / `interface_pico.interface_pico` | Actif | Exposer les topics et services Pico, puis traduire les commandes ROS 2 vers UART |
| `arbitre_commande_moteurs` | `robot_devastator` | `arbitre_commande_moteurs` / `robot_devastator.arbitre_commande_moteurs` | Actif | Sélectionner une seule source moteur active avant `/pico/commande_moteurs` |
| `evitement_obstacle` | `robot_devastator` | `evitement_obstacle` / `robot_devastator.evitement_obstacle` | Expérimental | Avancer lentement, balayer avec la tourelle, puis tourner jusqu'à trouver un dégagement |
| `teleop_clavier` | `robot_devastator` | `teleop_clavier` / `robot_devastator.teleop_clavier` | Actif | Conduire localement au clavier et basculer entre mode manuel et autonomie |
| `annonces_audio` | `robot_devastator` | `annonces_audio` / `robot_devastator.annonces_audio` | Actif | Préparer les WAV manquants avec Piper, puis jouer les annonces selon les événements du robot |
| `odometrie` | `odometrie` | `odometrie` / `odometrie.odometrie` | Actif (Phase 6) | Calculer x, y, theta depuis `/pico/encodeurs` et publier `/odom` et la TF `odom → base_footprint` |

## Interfaces personnalisées

| Interface | Type | Rôle |
|---|---|---|
| `commun/msg/ConsigneMoteurs` | Message | Transporter les consignes moteur gauche et droite, sur une plage prévue de `-1000` à `1000` |
| `commun/msg/EtatEncodeurs` | Message | Transporter les ticks des encodeurs gauche et droit publiés par `interface_pico` |

## Utilisation avec VSCode (via Quick Access - F1)

### Build

Les tâches disponibles sont définies dans `.vscode/tasks.json`.

- `Tasks: Run Build Task > ROS 2 - Build Devastator`
- `Tasks: Run Task > ROS 2 - Build complet`

### Nettoyage ciblé

- `Tasks: Run Task > ROS 2 - Nettoyer packages Devastator`

Utiliser ce nettoyage après modification, suppression ou renommage d'un `.msg` ou `.srv`, ou si
ROS 2 semble conserver des artefacts obsolètes dans `build/` ou `install/`.

### Simulation Gazebo (Legion-Linux)

- `Tasks: Run Task > ROS 2 - Lancer simulation Gazebo`

C'est la seule tâche VSCode d'exécution, réservée au diagnostic visuel sans matériel. Tous les
nœuds du robot réel se lancent en terminal sur le Raspberry Pi 4, jamais depuis VSCode.

### Debug d'un nœud Python

Les configurations de `.vscode/launch.json` servent seulement au debug direct d'un nœud Python
précis avec F5 :

`Nœud Python ROS 2` demande le module Python à exécuter, par exemple
`robot_devastator.evitement_obstacle`, `robot_devastator.annonces_audio` ou
`interface_pico.interface_pico`.

### Lancement du robot (terminal, Raspberry Pi 4)

Les assemblages ROS 2 sont centralisés dans `robot_devastator_bringup`. Démarrer le robot avec
téléopération tient en deux commandes, dans deux terminaux SSH :

```bash
# Terminal 1 : robot complet
ros2 launch robot_devastator_bringup devastator.launch.yaml

# Terminal 2 : conduite clavier en avant-plan
ros2 launch robot_devastator_bringup teleop.launch.yaml
```

Le lancement primaire `devastator.launch.yaml` démarre `interface_pico`, l'odométrie, l'arbitre
moteur, l'autonomie simple en attente et les annonces audio. Le mode initial est manuel.
`teleop.launch.yaml` se lance à part parce que `teleop_clavier` capture les touches du terminal
courant : c'est l'exception documentée au principe du lancement primaire unique. La touche `m`
bascule entre `manuel` et `autonomie`. L'arbitre publie seul vers `/pico/commande_moteurs`, ce qui
évite un conflit entre le clavier et `evitement_obstacle`.

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

Au lancement principal, `annonces_audio` est la seule capacité audio active. Le nœud charge les
annonces configurées dans `config/annonces_audio.yaml`, vérifie le cache persistant
`~/.cache/robot_devastator/audio`, puis génère synchroniquement avec Piper les fichiers WAV
manquants avant d'écouter `/robot/evenement`. Les WAV présents sont réutilisés aux lancements
suivants afin de ne pas ralentir le comportement du robot sur Raspberry Pi 4. Les annonces peuvent
proposer plusieurs variantes ; une chaîne vide représente une variante silencieuse. Si Piper, le
modèle vocal ou `aplay` sont absents, l'erreur est journalisée et l'audio reste décoratif : les autres
nœuds du robot ne dépendent pas de la génération ni de la lecture audio.

Diagnostic audio I2S validé : la sortie fonctionne avec `dtparam=i2s=on` et
`dtoverlay=hifiberry-dac`, et le HiFiBerry DAC est détecté comme carte ALSA. Le test fonctionnel
Devastator est :

```bash
aplay -D default ~/.cache/robot_devastator/audio/demarrage_01.wav
```

Limitation connue : l’ampli I2S produit un clac au début de chaque lecture audio.
Tests déjà effectués :
- audremap non retenu, I2S fonctionnel avec hifiberry-dac ;
- carte ALSA détectée ;
- lecture Devastator fonctionnelle avec aplay -D default ;
- clac présent à chaque lecture ;
- tentative via SD/shutdown non concluante ;
- tentative de lecture en stream non concluante ;
- changements annulés dans Git.

Décision :
- ne pas poursuivre ce chantier maintenant ;
- conserver l’audio comme capacité décorative.

## Visualisation URDF dans RViz (Legion-Linux)

Le package `robot_devastator_description` contient la description URDF/Xacro du robot et un
lancement RViz pour la visualiser sans matériel.

```bash
colcon build --symlink-install --packages-select robot_devastator_description
source install/setup.bash
ros2 launch robot_devastator_description affichage.launch.py
```

Dans RViz : ajouter un affichage **RobotModel**, fixer le **Fixed Frame** à `base_footprint`.
`joint_state_publisher_gui` ouvre une fenêtre pour faire tourner les roues manuellement.

## Commandes CLI utiles hors VSCode

Ces commandes restent utiles pour un diagnostic rapide hors VSCode, surtout pour l'exécution sur le Raspberry Pi.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico odometrie robot_devastator robot_devastator_bringup
source install/setup.bash
```

```bash
ros2 launch robot_devastator_bringup devastator.launch.yaml
ros2 launch robot_devastator_bringup teleop.launch.yaml
ros2 launch robot_devastator_bringup diag_interface_pico.launch.yaml
```

```bash
# Roues dans le vide : essai bref à faible vitesse, suivi d'un arrêt explicite attendu.
ros2 run interface_pico essai_moteurs_borne
ros2 service call /pico/ping std_srvs/srv/Trigger
ros2 service call /pico/stop_moteurs std_srvs/srv/Trigger
```

Procédure courte sur Raspberry Pi 4 avec le firmware Pico récent :

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico odometrie robot_devastator robot_devastator_bringup
source install/setup.bash
ros2 launch robot_devastator_bringup diag_interface_pico.launch.yaml
```

Dans d'autres terminaux sourcés, garder les roues dans le vide et un arrêt accessible :

```bash
ros2 service call /pico/ping std_srvs/srv/Trigger
ros2 service call /pico/stop_moteurs std_srvs/srv/Trigger
ros2 topic pub --once /pico/commande_moteurs commun/msg/ConsigneMoteurs \
  "{gauche: 200, droite: 200}"
ros2 topic echo /pico/distance_ultrason_mm
ros2 service call /pico/reset_encodeurs std_srvs/srv/Trigger
ros2 topic echo /pico/encodeurs
ros2 topic pub --once /pico/commande_moteurs commun/msg/ConsigneMoteurs \
  "{gauche: -200, droite: -200}"
ros2 service call /pico/stop_moteurs std_srvs/srv/Trigger
```

Téléopération clavier permanente, adaptée à un terminal local ou SSH :

```bash
# Terminal 1 : robot lancé, autonomie en attente du mode autonomie.
ros2 launch robot_devastator_bringup devastator.launch.yaml
```

```bash
# Terminal 2 : conduite clavier en avant-plan.
ros2 launch robot_devastator_bringup teleop.launch.yaml
```

Variante de diagnostic sans lancement principal :

```bash
# Terminal 1
ros2 run robot_devastator arbitre_commande_moteurs

# Terminal 2
ros2 launch robot_devastator_bringup teleop.launch.yaml
```

Touches QWERTY disponibles : `w` avance, `s` recule, `a` tourne à gauche, `d` tourne à droite,
`espace` arrête, `=` augmente la vitesse, `-` diminue la vitesse, `m` bascule entre conduite
manuelle et autonomie, `x` quitte. La vitesse par défaut est `300`, bornée de `300` à `1000` par
`config/teleop_clavier.yaml`. En mode manuel, `=` et `-` appliquent immédiatement la nouvelle
vitesse à la consigne de mouvement active. En mode autonomie, les touches de mouvement sont
ignorées, mais `m`, `=` et `-` restent actives pour revenir au manuel ou préparer la vitesse
manuelle. Garder les roues dans le vide au premier essai. À la sortie normale ou avec `Ctrl+C`,
l'outil publie un arrêt moteur explicite.

Les ticks doivent augmenter en marche avant et diminuer en marche arrière. Si un moteur tourne dans
le mauvais sens, corriger le câblage au MDD3A plutôt que le logiciel.

## Documentation détaillée

- [Carte ROS 2 pour l'apprentissage](docs/carte_ros_apprentissage.md)
- [Journal des essais](docs/journal_essais.md)
- [Architecture cible](docs/architecture_cible.md)
- [Paramètres techniques](docs/parametres.md)
- [Connexions des composantes matérielles](docs/connexions.md)
- [Inventaire des composantes matérielles principales](docs/inventaire_composantes.md)
