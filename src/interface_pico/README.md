# interface_pico

`interface_pico` est le package ROS 2 qui relie le Raspberry Pi 4 au Raspberry Pi Pico WH en UART.

## Rôle des fichiers principaux

- `interface_pico/transport_serie_pico.py` : couche UART brute. Ce fichier ouvre le port série, envoie les commandes texte terminées par fin de ligne et lit les lignes éventuelles renvoyées par le Pico.
- `interface_pico/interface_pico.py` : nœud ROS 2 `interface_pico_node`. Ce fichier adapte ROS 2 vers le transport série, expose les topics, services, paramètres et timers.

## Interfaces ROS 2

- Topic d'entrée `consigne_moteurs` : message `commun/msg/ConsigneMoteurs`
- Service `stop` : `std_srvs/srv/Trigger`
- Service `ping` : `std_srvs/srv/Trigger`
- Topic d'état `etat_pico` : `std_msgs/msg/String`

## Paramètres

- `port` : port série UART, par défaut `/dev/ttyS0`
- `debit` : débit UART, par défaut `115200`
- `timeout_lecture` : timeout de lecture série, par défaut `0.1`
- `periode_maintien_s` : période de renvoi de la dernière consigne, par défaut `0.1`

## Lancement

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select commun interface_pico
source install/setup.bash
ros2 launch interface_pico interface_pico.launch.py
```

## Test rapide

Publier une consigne moteur :

```bash
ros2 topic pub --once /consigne_moteurs commun/msg/ConsigneMoteurs "{gauche: 200, droite: 200}"
```

Tester les services :

```bash
ros2 service call /ping std_srvs/srv/Trigger
ros2 service call /stop std_srvs/srv/Trigger
```
