# interface_pico

`interface_pico` est le package ROS 2 qui relie le Raspberry Pi 4 au Raspberry Pi Pico WH en UART.

## Rôle des fichiers principaux

- `interface_pico/transport_serie_pico.py` : couche UART brute. Ce fichier ouvre le port
  série, envoie les commandes texte terminées par fin de ligne et lit les lignes éventuelles
  renvoyées par le Pico.
- `interface_pico/interface_pico.py` : nœud ROS 2 `interface_pico`. Ce fichier adapte
  ROS 2 vers le transport série, expose les topics, services, paramètres et timers.

## Interfaces ROS 2

- Topic d'entrée `/pico/commande_moteurs` : message `commun/msg/ConsigneMoteurs`
- Topic d'entrée `/pico/commande_tourelle_deg` : message `std_msgs/msg/Int32`, angle servo
  de tourelle en degrés de `0` à `180`
- Service `/pico/stop` : `std_srvs/srv/Trigger`
- Service `/pico/ping` : `std_srvs/srv/Trigger`, confirme l'envoi UART de `PING`, mais pas la
  réception d'une réponse du Pico
- Topic d'état `/pico/etat` : `std_msgs/msg/String`
- Topic publié `/pico/distance_ultrason_mm` : message `std_msgs/msg/Int32`, distance
  ultrason en millimètres lorsque le Pico répond à `DIST` par une ligne entière

## Paramètres

- `port` : port série UART, par défaut `/dev/ttyS0`
- `debit` : débit UART, par défaut `115200`
- `timeout_lecture` : timeout de lecture série, par défaut `0.1`
- `periode_maintien_s` : période de renvoi de la dernière consigne, par défaut `0.1`
- `delai_expiration_consigne_moteurs_s` : délai maximal sans nouvelle consigne ROS avant un arrêt
  explicite, par défaut `0.5`
- `periode_distance_s` : période des demandes `DIST`, par défaut `0.5`

Le lancement Devastator charge `config/interface_pico.yaml` depuis `robot_devastator_bringup`.
Les valeurs actives sont `0.02 s`, `0.25 s`, `0.5 s` et `0.10 s` pour ces quatre paramètres.

Le nœud répète temporairement la dernière consigne moteur afin de respecter le timeout du Pico.
Si aucune nouvelle consigne ROS n'arrive avant le délai d'expiration, il transmet et mémorise
un arrêt. Après une erreur ou une reconnexion UART, il repart aussi à l'arrêt et attend une
nouvelle consigne ROS avant d'autoriser un mouvement.

## Lancement dans Devastator

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico robot_devastator_bringup
source install/setup.bash
ros2 launch robot_devastator_bringup interface_pico.launch.yaml
```

Les fichiers de lancement et de paramètres sont centralisés dans `robot_devastator_bringup` pour
éviter plusieurs points d'entrée concurrents. Depuis VSCode, utiliser plutôt les tâches
`ROS 2 - Lancer interface Pico`.

La configuration de débogage `Nœud Python ROS 2` permet de lancer directement
`interface_pico.interface_pico` avec debugpy.

## Test rapide

Lancer uniquement avec les roues dans le vide. Le script applique une vitesse faible de `300`
pendant `1 s`, renouvelle cette consigne pendant l'essai, puis publie un arrêt explicite attendu.
La vitesse est volontairement limitée à `±300` et la durée à `2 s` au maximum.

```bash
ros2 run interface_pico essai_moteurs_borne
```

Tester les services :

```bash
ros2 service call /pico/ping std_srvs/srv/Trigger
ros2 service call /pico/stop std_srvs/srv/Trigger
```

Le succès de `/pico/ping` indique uniquement que la commande `PING` a été envoyée sur l'UART.
Observer `/pico/etat` pour vérifier la réception d'une réponse éventuelle du Pico.

Lire la distance ultrason :

```bash
ros2 topic echo /pico/distance_ultrason_mm
```

Tester les positions documentées du servo de tourelle :

```bash
ros2 topic pub --once /pico/commande_tourelle_deg std_msgs/msg/Int32 "{data: 95}"
ros2 topic pub --once /pico/commande_tourelle_deg std_msgs/msg/Int32 "{data: 45}"
ros2 topic pub --once /pico/commande_tourelle_deg std_msgs/msg/Int32 "{data: 140}"
```

La configuration active de l'autonomie utilise `95` pour le centre, `45` pour la gauche et `140`
pour la droite. Cette association a été validée physiquement sur le robot. Aucune logique de
balayage automatique ou d'évitement d'obstacle n'est ajoutée dans `interface_pico`.
