# Plan de formation Devastator

## Objectif

Construire Devastator par étapes pédagogiques pour adopter une posture d'ingénieur
robotique : comprendre l'architecture, les interfaces, les flux de données, les diagnostics
et les critères de validation — pas seulement écrire du code ROS 2.

## Règles

- Une case se coche uniquement après test observable (robot réel ou simulation)
  ou validation explicite en séance.
- Une note courte (date + observation clé) accompagne idéalement chaque case cochée.
- L'ordre des phases 2 à 10 est réfléchi : chaque phase prépare la suivante.
  L'ordre des phases 11+ est indicatif, à réviser au moment venu.
- Un concept se comprend avant de coder. Chaque phase explique le « pourquoi »
  en langage concret, sans détour mathématique inutile.
- Claude Code coche les cases sur demande explicite uniquement.

## Hors cible Devastator

- `ros2_control` et son `hardware_interface` : réécriture lourde sans gain pédagogique
  net ici, car `interface_pico` + UART joue déjà ce rôle. Réservé au projet RobotPi.
- Navigation parfaitement robuste, SLAM finement réglé, vision 3D complète,
  interaction vocale avancée : explorables mais non visés en production.

---

## Phase 0 — Fondation (infrastructure et sécurité) ✓

**Concept :** un robot est une chaîne de responsabilités séparées. Chaque maillon
(microcontrôleur, ROS 2, actionneurs) a un rôle précis et une frontière d'interface
documentée.

- [x] Chaîne UART Pi 4 → Pico WH → MDD3A → moteurs fonctionnelle
- [x] Watchdog sécurité moteur (500 ms côté Pico et côté `interface_pico`)
- [x] Contrat UART documenté (`docs/contrat_pico_ros2.md`)
- [x] Arbitre commandes moteurs (une seule source active)
- [x] Téléopération clavier permanente (`teleop_clavier`)
- [x] Annonces audio (`annonces_audio` + Piper + MAX98357)
- [x] Autonomie simple au sonar (`evitement_obstacle` — expérimental)
- [x] Validation `interface_pico.launch.yaml` roues dans le vide

**Livre :** _ROS 2 from Scratch_ — topics, services, nœuds, packages.

---

## Phase 1 — Consolidation documentaire ✓

**Concept :** un projet non documenté n'est pas transmissible. La documentation
courte et précise est une compétence d'ingénieur, pas une corvée.

- [x] `README.md` pour `commun`, `robot_devastator`, `robot_devastator_bringup`
- [x] `CLAUDE.md` pont dans les deux dépôts
- [x] `PLAN.md` intégré et lu par Claude en séance

---

## Phase 2 — Encodeurs et diagnostic

**Concept :** un encodeur en quadrature est un compteur de pas qui connaît son sens.
Il ne mesure pas une vitesse — il mesure un déplacement discret en ticks. La vitesse
se déduit en observant combien de ticks changent par unité de temps. C'est la donnée
la plus brute du robot ; tout le reste se construit dessus.

- [x] Ticks bruts confirmés sur `/pico/encodeurs` en faisant rouler le robot
- [x] Cohérence des signes validée : avance → deux côtés positifs ;
      recul → deux côtés négatifs ; rotation droite → signes opposés
- [x] Nœud `diagnostic_encodeurs` (réf. `scripts/test_encodeurs.py`): affiche ticks cumulés, delta par cycle, vitesse estimée en ticks/s
- [x] Service `/pico/reset_encodeurs` testé : les ticks reviennent à zéro

**Validation minimale :** pousser le robot d'environ 1 m à la main, lire les ticks,
remettre à zéro. Résultat répétable et cohérent en signe.
**Livre :** _Learn Robotics Programming 3e_ — capteurs et encodeurs.

---

## Phase 3 — Paramètres mécaniques et étalonnage

**Concept :** avant de calculer une distance, il faut connaître le robot. Trois nombres
transforment des ticks en mètres : le diamètre de roue, l'entraxe (distance entre les
deux roues) et la résolution d'encodeur (ticks par tour). Une erreur ici se propage
dans toute l'odométrie. C'est l'étape la plus souvent négligée et la première cause
d'odométrie fausse chez les makers.

- [x] Diamètre de roue mesuré au pied à coulisse, ticks/m calculé
- [x] Entraxe mesuré (distance entre points de contact au sol)
- [x] Résolution encodeur confirmée (ticks par tour complet de roue)
- [x] Paramètres consignés dans `docs/parametres.md` et un YAML dédié
- [x] Validation croisée : robot avancé d'exactement 1 m au ruban →
      ticks réels ≈ ticks théoriques (tolérance ±5 %)

**Validation minimale :** test sur surface plane, distance mesurée physiquement.
**Livre :** _Learn Robotics Programming 3e_ — cinématique différentielle intuitive.

---

## Phase 4 — Description du robot et visualisation (URDF/Xacro + TF + RViz)

**Concept :** le TF est l'arbre généalogique du robot : chaque pièce connaît sa position
par rapport à sa pièce parente. L'URDF est la description physique qui permet à ROS 2
de construire cet arbre, et Xacro la rend paramétrable. RViz dessine le robot à partir
de ces données. À ce stade, les roues sont bougées « à la main » via
`joint_state_publisher_gui` — pas encore de physique.

- [ ] URDF/Xacro minimal : `base_footprint`, `base_link`, deux roues, tourelle
- [ ] `robot_state_publisher` lancé, `/robot_description` publié
- [ ] Arbre TF cohérent vérifié (`ros2 run tf2_tools view_frames`)
- [ ] RViz : modèle visible, proportions et orientation correctes
- [ ] RViz : `joint_state_publisher_gui` fait tourner les roues à l'écran

**Validation minimale :** le robot apparaît dans RViz, les roues bougent avec les
curseurs. Aucun matériel requis — entièrement sur Legion-Linux.
**Livre :** _Mastering ROS 2 4e_ — chapitres URDF, Xacro, TF.

---

## Phase 5 — Simulation Gazebo (étalon visuel)

**Concept :** la simulation transforme la description en robot physique : gravité,
collisions, moteurs simulés. Point clé pour l'apprentissage : le plugin DiffDrive de
Gazebo **fournit gratuitement l'odométrie** (`/odom` et la transform `odom → base_link`).
Tu vois donc une trajectoire propre AVANT d'avoir écrit le moindre calcul. La simulation
devient ton étalon de référence : quand tu coderas l'odométrie réelle en Phase 6,
tu sauras exactement à quoi le résultat doit ressembler.

> Utiliser le plugin **DiffDrive simple** de Gazebo, PAS `ros2_control`
> (déroutant pour débuter et hors cible Devastator).

- [ ] Balises `<inertial>` et `<collision>` ajoutées à l'URDF (formes simples)
- [ ] Robot apparaît (`spawn`) dans un monde Gazebo vide
- [ ] Plugin DiffDrive configuré : le robot roule via `/cmd_vel`
- [ ] Pilotage en simulation depuis Legion-Linux (clavier ou `teleop`)
- [ ] Trajectoire `/odom` visible dans RViz pendant le déplacement simulé

**Validation minimale :** conduire le robot simulé en cercle, voir la trajectoire
se tracer dans RViz. Entièrement sur Legion-Linux, aucun risque matériel.
**Livre :** _Mastering ROS 2 4e_ — chapitres simulation et Gazebo.

---

## Phase 6 — Odométrie sur le robot réel

**Concept :** l'odométrie est le « comptage de pas » du robot. En combinant les ticks
gauche et droite avec les paramètres mécaniques de la Phase 3, on estime où le robot
est allé depuis son départ — sans GPS ni caméra. Cette estimation dérive avec le temps
(comme marcher les yeux fermés), mais c'est la base de toute navigation. Tu reproduis
maintenant sur Devastator réel ce que Gazebo t'a montré en Phase 5.

- [ ] Nœud `odometrie` publiant `/odom` (`nav_msgs/Odometry`)
- [ ] Transform `odom → base_link` publiée par le même nœud
- [ ] Validation avance : ~1 m réel → X entre 0,95 et 1,05 m dans `/odom`
- [ ] Validation rotation : ~90° sur place → yaw entre 1,47 et 1,67 rad
- [ ] Dérive documentée : carré de 2 m de côté, écart de retour mesuré

**Validation minimale :** trajectoire en carré visible dans RViz (Legion-Linux
connecté au Pi via SSH). La dérive est attendue et documentée, pas corrigée.
**Livre :** _Learn Robotics Programming 3e_ + _Régulation PID par la pratique_
(notion de mesure et d'erreur, pas encore de réglage PID).

---

## Phase 7 — Surveillance de l'alimentation (INA260)

**Concept :** un robot sans surveillance de sa tension peut endommager ses batteries
ou tomber en panne sans avertir. L'INA260 mesure tension et courant en temps réel via
le bus I2C. Sous-système simple, immédiatement utile, bon exercice d'intégration capteur.

- [ ] INA260 câblé et détecté sur l'I2C du Pi 4 (`i2cdetect`)
- [ ] Nœud `surveillance_alimentation` publiant tension et courant
- [ ] Seuil d'alerte bas testé (annonce audio ou log)
- [ ] Lecture cohérente avec le voltmètre physique existant

**Validation minimale :** tension publiée ≈ tension lue au voltmètre.
**Livre :** _Learn Robotics Programming 3e_ — interfaces I2C.

---

## Phase 8 — Affichage local (LCD Waveshare 2" ST7789V)

**Concept :** un robot qui affiche son état localement se diagnostique sur le terrain
sans SSH. L'écran LCD est un sous-système de sortie simple : il reçoit un état ROS 2
et l'affiche. Bon exercice de nœud abonné (subscriber) avec sortie matérielle.

- [ ] LCD ST7789V initialisé, affichage texte basique
- [ ] Nœud `affichage_lcd` abonné au mode et à l'état du robot
- [ ] Pages minimales : mode actif, tension, état moteurs
- [ ] Transition entre pages documentée

**Validation minimale :** basculer manuel/autonomie → l'affichage change.
**Livre :** _Learn Robotics Programming 3e_ — affichages embarqués.

---

## Phase 9 — Perception lidar (RPLIDAR A1M8)

**Concept :** le lidar balaye l'environnement à 360° et publie des distances sous forme
de nuage de points 2D (`LaserScan`). C'est le capteur principal de la cartographie et
de la navigation. Cette phase valide uniquement la chaîne de données et le placement
dans l'arbre TF — pas encore la navigation.

- [ ] RPLIDAR dégelé, pilote ROS 2 installé
- [ ] Scan publié sur `/scan` (`sensor_msgs/LaserScan`)
- [ ] Transform `base_link → laser` ajoutée à l'URDF
- [ ] Scan visible et stable dans RViz (le mur en face est reconnaissable)
- [ ] Qualité documentée : portée effective, zones mortes

**Validation minimale :** faire tourner le robot ; les objets fixes restent stables
dans RViz pendant que le scan tourne.
**Livre :** _Mastering ROS 2 4e_ — capteurs et LaserScan.

---

## Phase 10 — Navigation autonome (Nav2)

**Concept :** Nav2 est le « GPS intérieur » du robot. Il combine une carte, une position
estimée (odométrie) et un capteur (lidar) pour planifier un chemin et guider le robot
vers un objectif sans intervention. C'est l'aboutissement des phases précédentes.
On le teste d'abord en simulation (sûr), puis sur le robot réel.

> **Prérequis stricts :** Phases 5, 6 et 9 complètes.

- [ ] Carte créée avec `slam_toolbox` (en simulation d'abord)
- [ ] Nav2 minimal lancé sur la carte statique
- [ ] Navigation vers un point fixé dans RViz (2D Nav Goal) en simulation
- [ ] Portage et test sur le robot réel dans une pièce connue
- [ ] Comportement de récupération documenté (robot bloqué ?)
- [ ] Paramètres clés documentés (vitesse max, rayon d'inflation)

**Validation minimale :** aller-retour autonome entre deux points connus d'une pièce
connue, sans intervention humaine.
**Livre :** _Mastering ROS 2 4e_ — Nav2 et SLAM.

---

## Phase 11 — Perception 3D (RealSense D435IF) — exploratoire

**Concept :** la caméra de profondeur voit les obstacles en hauteur (bords de table,
jambes) que le lidar 2D manque. Phase exploratoire ; l'intégration complète dans Nav2
est hors cible Devastator.

- [ ] Pilote RealSense ROS 2 installé, flux publié
- [ ] Nuage de points visible dans RViz
- [ ] Cas d'usage minimal documenté (détection d'obstacle vertical)

**Livre :** _Mastering ROS 2 4e_ — caméras et PointCloud.

---

## Phase 12 — Réception vocale (ReSpeaker + Alexa) — exploratoire

**Concept :** le ReSpeaker capte la voix avec annulation d'écho et formation de faisceau
(plusieurs micros qui collaborent). Complément à la synthèse Piper déjà active.

- [ ] ReSpeaker Mic Array v3.0 initialisé, audio capté
- [ ] Détection de mot déclencheur (wake word)
- [ ] Commande vocale simple liée à un événement ROS 2

**Livre :** _Programming Voice-Controlled IoT Applications_ — Alexa sur Raspberry Pi.

---

## Socle conceptuel (à lire avant la phase indiquée)

### Avant Phase 4 — TF : l'arbre généalogique du robot
À lire en séance avec Claude. Durée : 20 minutes.
Objectif : comprendre ce qu'est un frame, une transform et un arbre TF
avant de toucher un seul fichier URDF.

### Avant Phase 6 — Sin/cos comme décomposition de direction
À lire en séance avec Claude. Durée : 15 minutes.
Objectif : comprendre intuitivement comment une direction s'exprime
en composantes X et Y, sans mémoriser une formule.

### En continu — Topics vs services vs actions : le bon outil au bon moment
À revisiter à chaque nouvelle interface dans le projet.
Objectif : que le choix devienne un réflexe ancré dans Devastator,
pas une règle abstraite mémorisée.

---

## Trajectoire de progression

### Devastator (en cours)
Chenilles, 2 moteurs 6V, diff-drive, Pi 4.
Objectif : comprendre la recette complète d'un robot mobile ROS 2.
Certaines parties resteront imparfaites — c'est voulu.

### RobotPi (suivant)
4 roues mecanum, 4 moteurs 12V, Pi 5.
Cinématique holonomique, ros2_control, alimentation Pi 5 à résoudre.
Pièces déjà acquises pour la plupart. Concevoir en tirant les leçons de Devastator.

### Pupper V3 (après RobotPi)
Quadrupède Stanford. Cinématique inverse, génération de démarche.
Prérequis : maîtrise TF, URDF et Nav2 acquise sur Devastator + RobotPi.

### LeRobot Hugging Face (parallèle)
Apprentissage des concepts IA en parallèle de Devastator et RobotPi. 

---

## Leçons pour RobotPi

Ce que Devastator m'a appris que je ferais différemment dès la conception.
À compléter au fil du projet — une ligne par décision significative.

- Chenilles : entraxe effectif non mesurable précisément → préférer roues pour odométrie fiable.
- Pico WH : contrat UART maison efficace mais à remplacer par ros2_control sur plateforme plus mature.
- Alimentation Pi 5 : résoudre avant conception, pas pendant.

---

## Décisions et contexte

Format : `YYYY-MM-DD — décision ou observation clé (une ligne)`

- 2026-06-22 — Plan enrichi : ordre validé (URDF → Gazebo → odométrie réelle),
  simulation placée en étalon visuel, `ros2_control` écarté (RobotPi).
- 2026-06-22 — PLAN.md adopté comme source unique de progression.
- 2026-06-10 — Arbitre moteur validé comme point central unique.
- 2026-06-10 — Autonomie simple expérimentale, démarre en mode attente.