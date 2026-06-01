# État actuel — Devastator

## Objectif actuel

Mettre en place une autonomie simple au sonar, sans intégrer de complexité avancée, mais en posant
la base de la structure du projet de façon modulaire pour permettre de la faire évoluer peu à peu
avec de nouvelles composantes. L'ambition est également de récupérer des modules dans d'autres
projets de robots avec ROS 2.

Comportement cible immédiat :

1. avancer lentement
2. détecter un obstacle devant le robot avec une bonne marge
3. arrêter le robot
4. orienter le sonar à gauche, au centre puis à droite avec prise de mesure fraîche
5. comparer les distances mesurées
6. recentrer le sonar et tourner vers le côté le plus dégagé
7. confirmer le dégagement avant seulement après une durée minimale de rotation
8. reculer brièvement et refaire le balayage si la rotation ne trouve aucun dégagement
9. retour à l'étape 1

L’objectif du moment n’est pas encore de faire de la navigation ROS 2 avancée, de l’odométrie,
du PID, du lidar, de la caméra ou de la cartographie.

## Matériel actif pouvant être utilisé

Voir la section [composantes active de l'inventaire](inventaire_composantes.md)

## Ce qui est fonctionnel et testé

- l'autonomie simple au sonar sur le robot réel. Le comportement fonctionne relativement bien
  avec les paramètres actuels, qui restent empiriques ;
- le firmware du Raspberry Pi Pico WH testé avec `picocom` à partir du Raspberry Pi 4. Les services suivants du protocole UART sont testés:
    - `PING`
    - `STOP`
    - `SET <gauche> <droite>`
    - `STATUS`
    - `DIST`
    - `SERVO <angle>`
- L'intégration des topics ROS suivants :
    - `/pico/commande_moteurs`
    - `/pico/commande_tourelle_deg`
    - `/pico/distance_ultrason_mm`
    - `/pico/etat`
- L'intégration des services ROS suivants :
    - `/pico/ping`
    - `/pico/stop`

## Prochaine validation ciblée

Après toute modification du comportement, revalider physiquement l'autonomie simple avec les roues
dans le vide :

1. placer un obstacle devant le sonar ;
2. vérifier l'arrêt explicite des moteurs ;
3. vérifier les mesures fraîches à gauche, au centre, puis à droite ;
4. vérifier le recentrage du sonar avant la rotation vers le côté le plus dégagé ;
5. vérifier que la rotation dure au moins `0,6 s` ;
6. publier trois mesures consécutives d'au moins `600 mm` et vérifier l'arrêt de la rotation ;
7. vérifier que l'avance reprend seulement lorsque la mesure avant est valide et dégagée ;
8. refaire un essai sans dégagement et vérifier le recul bref après `4,0 s`, puis un nouveau
   balayage.

Les angles de tourelle, le délai de stabilisation, les vitesses, la distance de dégagement et les
durées restent empiriques. Ils doivent être ajustés progressivement sur le Raspberry Pi 4 avec le
robot sécurisé. Les vitesses moteur ne doivent pas être réduites sous environ `300` sans nouvelle
validation physique.
