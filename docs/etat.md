# État actuel — Devastator

## Objectif actuel

Mettre en place une autonomie simple au sonar, sans intégrer de complexité avancée, mais en posant 
base de la structure du projet de façon très modulaire permettant ainsi de la faire évoluer peu à 
peu en complexité, avec de plus en plus de composantes. Ambition également de récupérer des modules
dans d'autres projets de robot avec ROS 2.

Comportement cible immédiat :

1. avancer lentement
2. détecter un obstacle devant le robot avec une bonne marge 
3. arrêter le robot
4. orienter le sonar à gauche puis à droite avec prise de mesure
5. comparer les distances mesurées
6. tourner vers le côté le plus dégagé
7. retour à l'étape 1

L’objectif du moment n’est pas encore de faire de la navigation ROS 2 avancée, de l’odométrie, 
du PID, du lidar, de la caméra ou de la cartographie. 

## Matériel actif pouvant être utilisé

Voir la section [composantes active de l'inventaire](inventaire_composantes.md)

## Ce qui est fonctionnel et testé

- le firmware du Raspberry Pi Pico WH testé avec `picocom` à partir du Raspberry Pi 4. Les services suivants du protocole UART sont testés:
    - `PING`
    - `STOP`
    - `SET <gauche> <droite>`
    - `STATUS`
    - `DIST`
    - `SERVO <angle>`
- L'intégration des topics ROS suivants: 
    - `/pico/commande_moteurs`
    - `/pico/commande_tourelle_deg`
    - `/pico/distance_ultrason_mm`
    - `/pico/etat`
- L'intégration des services ROS suivants: 
    - `/pico/ping`
    - `/pico/stop`

## Prochain test

Lorsque obstacle détecter, orienter le sonar à gauche puis à droite avec prise de mesure pour chacune de ces position puis tourner l'équivalent de 45 degrés (on va y aller approximativement ou empiriquement pour l'instant) dans la direction où la valeur retournée est la plus élevé (donc la direction qui apparaît la plus dégagée). Ensuite, on poursuit l'avancement en ligne droite.