# Contrat Pico WH ↔ ROS 2

## Rôle de `interface_pico`

`interface_pico` est le pont entre ROS 2 sur le Raspberry Pi 4 et le firmware du Pico WH par
UART texte. Il expose des topics et services ROS 2, valide les plages simples, envoie les commandes
ASCII au Pico, lit les lignes UART reçues et republie les informations utiles dans ROS 2.

Il traduit dans les deux sens : commandes ROS 2 vers commandes UART, et réponses/événements UART vers topics ou réponses de services ROS 2.

Le nœud ne décide pas du comportement du robot. Il ne fait pas d'évitement d'obstacle, ne calcule
pas d'odométrie et ne corrige pas le sens des moteurs en logiciel.

## Responsabilités

| Côté | Responsabilités |
|---|---|
| Raspberry Pi 4 | Exécuter ROS 2 Jazzy, lancer `interface_pico`, publier les consignes, appeler les services, maintenir temporairement la dernière consigne moteur, forcer l'arrêt après expiration d'une consigne ROS et rouvrir la liaison UART si possible. |
| Pico WH | Recevoir le protocole UART, piloter les moteurs via le MDD3A, orienter le servo de tourelle, mesurer le sonar, lire les encodeurs et appliquer son propre arrêt de sécurité si aucune commande UART valide n'arrive depuis plus de `500 ms`. |

## Topics ROS 2

### Topics consommés par `interface_pico`

| Topic | Type | Effet UART |
|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | Envoie `SET_MOT <gauche> <droite>` si les deux valeurs sont entre `-1000` et `1000`. |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Envoie `SET_SERVO <angle>` si l'angle est entre `0` et `180`. |

### Topics publiés par `interface_pico`

| Topic | Type | Source UART |
|---|---|---|
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | Réponse `OK SONAR <distance_mm>`. |
| `/pico/encodeurs` | `commun/msg/EtatEncodeurs` | Réponse `OK ENC <gauche_ticks> <droite_ticks>`. |
| `/pico/etat` | `std_msgs/msg/String` | Toute ligne UART reçue du Pico, incluant les réponses `OK ...`, `READY`, `AVERT TIMEOUT`, `AVERT`, `WARN` et `ERREUR`. |

## Services ROS 2 fournis

| Service | Type | Commande UART | Succès attendu |
|---|---|---|---|
| `/pico/ping` | `std_srvs/srv/Trigger` | `PING` | `OK PING` reçu avant `delai_attente_reponse_service_s`. |
| `/pico/stop_moteurs` | `std_srvs/srv/Trigger` | `STOP_MOT` | `OK STOP_MOT` reçu avant `delai_attente_reponse_service_s`. |
| `/pico/reset_encodeurs` | `std_srvs/srv/Trigger` | `RESET_ENC` | `OK RESET_ENC` reçu avant `delai_attente_reponse_service_s`. |

## Protocole UART

Les commandes sont du texte ASCII terminé par un saut de ligne.

| Usage | Commande envoyée | Réponse normalisée attendue |
|---|---|---|
| Test de liaison | `PING` | `OK PING` |
| Arrêt moteur explicite | `STOP_MOT` | `OK STOP_MOT` |
| Commande moteurs | `SET_MOT <gauche> <droite>` | `OK SET_MOT <gauche> <droite>` |
| Commande servo | `SET_SERVO <angle>` | `OK SET_SERVO <angle>` |
| Mesure sonar | `SONAR` | `OK SONAR <distance_mm>` |
| Lecture encodeurs | `ENC` | `OK ENC <gauche_ticks> <droite_ticks>` |
| Remise à zéro encodeurs | `RESET_ENC` | `OK RESET_ENC` |

`STATUS` est supporté par la couche de transport et par le décodeur de réponses avec le format
`OK STATUS <gauche> <droite> <actif>`, mais le nœud `interface_pico` actuel ne l'expose pas par
topic, service ou timer.

## Sécurité et erreurs connues

- Les consignes moteurs ROS 2 valides sont limitées à `-1000` à `1000`.
- Une consigne `0, 0` représente l'arrêt.
- `interface_pico` répète temporairement la dernière consigne moteur avec `periode_maintien_s`.
- Si aucune nouvelle consigne moteur ROS 2 n'arrive avant
  `delai_expiration_consigne_moteurs_s`, le nœud mémorise et envoie un arrêt.
- Au démarrage ou après reconnexion UART, `interface_pico` envoie `STOP_MOT`, mémorise l'arrêt et
  attend une nouvelle consigne ROS avant de relancer un mouvement.
- Après une erreur UART, le port est fermé, la consigne mémorisée devient `0, 0` et les tentatives
  suivantes essaient de rouvrir la liaison.
- À la destruction du nœud, `interface_pico` tente d'envoyer `STOP_MOT` avant de fermer le port.
- Les lignes `READY` et `AVERT TIMEOUT` du Pico sont publiées sur `/pico/etat` et journalisées.
- Le Pico applique aussi un arrêt automatique si aucune commande UART valide n'arrive depuis plus
  de `500 ms`, selon la documentation du dépôt.

## Paramètres importants

Valeurs actives avec `robot_devastator_bringup/config/interface_pico.yaml` :

| Paramètre | Valeur active | Défaut du nœud | Rôle |
|---|---:|---:|---|
| `port` | `/dev/ttyS0` | `/dev/ttyS0` | Port série matériel relié au Pico WH. |
| `debit` | `115200` | `115200` | Débit UART partagé avec le firmware Pico. |
| `timeout_lecture` | `0.02 s` | `0.1 s` | Attente maximale d'une lecture UART. |
| `periode_maintien_s` | `0.25 s` | `0.1 s` | Intervalle de rappel de la dernière consigne moteur. |
| `delai_expiration_consigne_moteurs_s` | `0.5 s` | `0.5 s` | Délai sans nouvelle consigne ROS avant arrêt explicite. |
| `periode_distance_s` | `0.10 s` | `0.5 s` | Intervalle des demandes `SONAR`. |
| `periode_encodeurs_s` | `0.10 s` | `0.1 s` | Intervalle des demandes `ENC`. |
| `delai_attente_reponse_service_s` | `1.0 s` | `1.0 s` | Délai maximal d'attente d'une confirmation de service. |

## Limites connues

- Aucune action ROS 2 n'est fournie par `interface_pico`.
- Aucune odométrie n'est calculée à partir des encodeurs.
- `STATUS` n'a pas de point d'entrée ROS 2 actuellement.
- Les réponses `SET_MOT`, `SET_SERVO` et `STATUS` sont validées et publiées sur `/pico/etat`,
  mais elles ne produisent pas de topic spécialisé.
- Le nœud ne publie pas d'état de connexion UART structuré.
- Le balayage de tourelle et l'évitement d'obstacle appartiennent à `robot_devastator`, pas à
  `interface_pico`.

## Validation CLI courte sur Raspberry Pi 4

Préparer le terminal :

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico robot_devastator_bringup
source install/setup.bash
ros2 launch robot_devastator_bringup interface_pico.launch.yaml
```

Dans d'autres terminaux sourcés :

```bash
ros2 service call /pico/ping std_srvs/srv/Trigger
ros2 topic echo /pico/etat
ros2 topic echo /pico/distance_ultrason_mm
ros2 topic echo /pico/encodeurs
ros2 service call /pico/reset_encodeurs std_srvs/srv/Trigger
ros2 topic pub --once /pico/commande_tourelle_deg std_msgs/msg/Int32 "{data: 95}"
ros2 service call /pico/stop_moteurs std_srvs/srv/Trigger
```

Essai moteur court seulement roues dans le vide, avec arrêt accessible :

```bash
ros2 run interface_pico essai_moteurs_borne
ros2 service call /pico/stop_moteurs std_srvs/srv/Trigger
```

## Critères d'acceptation observables

- `/pico/ping` retourne `success=True` avec confirmation `OK PING`.
- `/pico/etat` affiche les lignes UART reçues, par exemple `OK PING`, `OK STOP_MOT`, `READY` ou
  `AVERT TIMEOUT`.
- `/pico/distance_ultrason_mm` publie des entiers en millimètres lorsque le sonar répond.
- `/pico/encodeurs` publie `gauche_ticks` et `droite_ticks`.
- `/pico/reset_encodeurs` retourne `success=True` avec confirmation `OK RESET_ENC`.
- La commande tourelle à `95` est acceptée et confirmée par une ligne `OK SET_SERVO 95` sur
  `/pico/etat`.
- L'essai moteur borné fait tourner brièvement les roues dans le vide, puis publie un arrêt
  explicite.
- Après arrêt ou expiration de consigne, les moteurs cessent de tourner.

## Points ouverts

- Le dépôt ROS 2 documente le timeout Pico de `500 ms`, mais l'implémentation exacte est dans le
  firmware Pico, hors de ce workspace.
- Le sens exact d'évolution des ticks encodeurs dépend du câblage et du firmware Pico ; le README
  indique qu'ils doivent augmenter en marche avant et diminuer en marche arrière.
- Aucune procédure automatisée ne valide encore ce contrat sans matériel.
