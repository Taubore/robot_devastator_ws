# AGENTS.md — Consignes pour Codex

## Mission du projet

Devastator est un robot mobile réel servant de plateforme d’apprentissage en électronique,
robotique, Python, ROS 2 et systèmes embarqués.

Dépôt officiel : https://github.com/Taubore/robot_devastator_ws

Ce dépôt est le workspace ROS 2 officiel du projet. Il doit évoluer progressivement à partir
du code existant. Ne pas créer d’architecture parallèle et ne pas repartir de zéro.

## Sources à consulter avant modification

Avant toute modification non triviale, consulter selon le besoin :

1. `AGENTS.md` pour les règles de travail ;
2. `README.md` pour l’état documenté du workspace, les packages, les nœuds, les interfaces
   et les lancements ;
3. `docs/parametres.md` si la tâche touche aux GPIO, UART, PWM, seuils ou conventions ;
4. `docs/connexions.md` si la tâche touche au câblage ou au matériel ;
5. `docs/architecture_cible.md` si la tâche touche à l’organisation globale ou aux sous-systèmes
   futurs ;
6. `docs/inventaire_composantes.md` si la tâche touche au choix ou au statut des composants.

Le code réel et les fichiers de configuration présents dans le dépôt priment sur une documentation
possiblement désuète. Si une divergence est trouvée, Codex doit la signaler avant de modifier.

## Cible fonctionnelle finale

Devastator est un robot mobile d’apprentissage. Sa cible finale n’est pas d’être un robot parfaitement intégré ni un produit fini, mais une plateforme complète pour toucher concrètement à plusieurs sous-systèmes robotiques réutilisables.

Le projet sera considéré terminé lorsque les grandes familles suivantes auront été intégrées,
testées au moins à un niveau fonctionnel simple, puis documentées :

- base mobile ROS 2 fonctionnelle avec Raspberry Pi 4, Pico WH, moteurs FIT0521, MDD3A
  et arrêt fiable ;
- autonomie simple au sonar avec tourelle servo et comportement d’évitement d’obstacle ;
- lecture des encodeurs quadrature des moteurs via `interface_pico`, avec publication ROS 2
  exploitable ;
- téléopération par manette PS2 et/ou clavier de l'ordinateur Legion-Linux via SSH (Raspberry Pi 4 lorsque cela aide les essais matériels ;
- voix française avec Piper pour retours sonores simples ;
- affichage local sur module Waveshare LCD 2" ST7789V pour visage et pages d’état ;
- intégration du Slamtec RPLIDAR A1M8 pour découverte de la chaîne lidar, cartographie ou
  navigation ROS 2 simple ;
- intégration de la caméra RealSense D435IF pour découverte de la perception profondeur ;
- intégration du ReSpeaker Mic Array v3.0 pour expérimentation de réception vocale ;
- documentation suffisante pour réutiliser les modules utiles dans RobotPi ou un autre robot
  sans devoir relire tout le code.

Cette cible guide l’évolution du projet. Elle ne justifie pas une intégration prématurée. Chaque
sous-système doit être ajouté seulement lorsque l’étape courante le rend utile, avec une validation
physique courte, observable et sécuritaire.

## Limites de la cible

Devastator reste un banc d’apprentissage. Il est acceptable qu’un sous-système soit validé de façon
minimale plutôt que poussé jusqu’à une solution industrielle complète.

Ne pas viser sur Devastator :

- navigation autonome complète et robuste ;
- SLAM parfaitement réglé ;
- interaction vocale avancée ;
- vision 3D complète ;
- interface graphique complexe ;
- architecture générique abstraite avant usage réel.

Ces sujets peuvent être explorés, mais Devastator doit rester pédagogique, progressif et maintenable. Le projet RobotPi ira plus loin dans le futur.

## Principe de progression

Atteindre la cible finale par étapes pédagogiques, en ajoutant une seule complexité significative
à la fois.

Chaque nouvelle intégration doit respecter l’ordre suivant :

1. comprendre le rôle du composant ou du module ;
2. valider son fonctionnement minimal de façon isolée seulement si le risque le justifie ;
3. l’intégrer dans ROS 2 avec une interface simple ;
4. tester le comportement sur le robot réel ;
5. documenter l’usage, les paramètres et les limites.

L’ordre d’intégration doit suivre la dépendance réelle entre les sous-systèmes : alimentation,
sécurité, actionneurs, mesures, contrôle, perception, décision, puis comportements plus avancés.

Un sous-système déjà validé est considéré acquis jusqu’à symptôme contraire. Ne pas répéter ses
tests de base si le changement ne le touche pas.

Codex doit privilégier les changements courts, testables et réversibles. L’architecture doit évoluer
à partir des besoins validés, pas à partir d’une cible idéale abstraite.

## Architecture directrice

L’architecture doit s’inspirer du modèle modulaire de Synthiam ARC : un robot est un assemblage
de capacités indépendantes, configurables, documentées et réutilisables. L’objectif est d’obtenir
une approche proche du low-code par l’usage, mais 100 % code, versionnée dans Git et adaptée
à ROS 2 Jazzy.

Principes :

- une capacité claire = un nœud ou package ROS 2 spécialisé ;
- configuration = paramètres ROS 2 et fichiers YAML ;
- assemblage du robot = fichiers `launch`, préférablement `*.launch.yaml` ;
- communication = topics pour les flux, services pour les demandes ponctuelles, actions pour
  les comportements longs ou annulables ;
- réutilisation = module non lié inutilement à Devastator ;
- pédagogie = code lisible, noms explicites, commentaires utiles et documentation courte.

Un module réutilisable doit fournir un contrat d’usage minimal :

- rôle du module ;
- paramètres YAML importants et bien documentés ;
- topics publiés et consommés ;
- services et actions, si présents ;
- exemple de lancement ;
- test simple ou commande de validation ;
- limites connues.

Séparation des responsabilités :

- capteur : lit ou publie une mesure brute ou normalisée ;
- perception : transforme les mesures en information exploitable ;
- décision : choisit une action ;
- actionneur : applique une commande au matériel ;
- bringup : assemble les modules, paramètres et variantes du robot.

Les différences propres à Devastator doivent rester dans les fichiers YAML, les fichiers `launch`
ou la couche `bringup`, pas dans les modules réutilisables.

Ne pas créer d’application monolithique. Ne pas créer de framework maison. Ne pas multiplier
les petits packages artificiels. Extraire une capacité seulement lorsqu’elle est claire, utile,
testable et susceptible d’être réutilisée.

## Structure du workspace

Le workspace ROS 2 doit évoluer progressivement à partir de la structure existante. La structure
actuelle n’est pas figée, mais toute évolution doit être justifiée par une responsabilité claire,
un besoin réel et un gain de lisibilité ou de réutilisation.

Principes :

- ne pas créer d’architecture parallèle ;
- ne pas repartir de zéro ;
- ne pas créer de package pour une responsabilité encore floue ;
- ne pas déplacer massivement du code sans plan validé ;
- extraire un module seulement lorsqu’il devient clair, testable et réutilisable ;
- garder le robot lançable et testable après chaque changement.

Les packages existants doivent être utilisés selon leur rôle actuel :

- `commun` : interfaces ROS 2 communes ;
- `interface_pico` : communication Raspberry Pi 4 ↔ Pico WH ;
- `robot_devastator` : logique principale et comportements propres au robot ;
- `robot_devastator_bringup` : assemblage des nœuds, paramètres et fichiers `launch`, lorsque
  disponible ou requis.

Codex peut proposer une évolution de structure si elle simplifie le projet durablement. Dans ce cas,
il doit expliquer :

1. le problème de structure observé ;
2. la nouvelle responsabilité proposée ;
3. les fichiers ou packages touchés ;
4. l’impact sur les lancements, paramètres et tests ;
5. le plan de migration minimal.

## Environnements

### Legion-Linux

Environnement principal de développement.

- Lenovo Legion Pro 5 16IRX9 Type 83DF, Intel Core i7-14650HX, 32 Go RAM,
  NVIDIA GeForce RTX 4060 Laptop GPU avec 8 Go VRAM
- Ubuntu 24.04
- ROS 2 Jazzy
- VSCode
- Profil VSCode : `ROS2`
- Rôle : édition, refactorisation, documentation, Codex, Git, tests sans matériel

### Raspberry Pi 4

Environnement d’intégration réelle.

- Raspberry Pi 4 Model B, 4 Go RAM
- Ubuntu 24.04
- ROS 2 Jazzy
- Accès via VSCode Remote SSH
- Rôle : exécution ROS 2, tests UART, Pico WH, moteurs, capteurs, validation physique

Tout code doit tenir compte de cette séparation : développement sur Legion-Linux, validation
matérielle sur Raspberry Pi 4.

## Environnement Python et ROS 2

- ROS 2 : Jazzy
- Python : 3.12.3
- Aucun `venv` pour le workspace ROS 2 principal
- Utiliser l’environnement Python système lié à ROS 2
- Ne pas ajouter de dépendance Python externe sans justification et validation
- Aviser s’il est préférable d’installer de nouvelles bibliothèques ou composantes dans un `venv`

## Règles ROS 2

- Respecter les conventions ROS 2 Jazzy
- Respecter les bonnes pratiques ROS 2, sans purisme ni abstraction inutile
- Utiliser les messages et services existants quand ils suffisent
- Ne pas créer de nouveaux `.msg` ou `.srv` sans nécessité claire
- Préférer les paramètres ROS 2 aux valeurs codées en dur
- Les nœuds doivent être lançables depuis VSCode ou via `ros2 launch`
- Éviter les longues séquences CLI sauf diagnostic, installation ou build nécessaire
- Documenter les interfaces ROS 2 lorsqu’elles deviennent des points d’intégration stables
- Garder les différences entre robots dans les paramètres YAML et les fichiers `launch`
- Regrouper les lancements complets du robot dans un package `bringup` lorsque plusieurs nœuds,
  paramètres ou sous-systèmes doivent être assemblés
- Préférer `*.launch.yaml` pour les lancements simples
- Utiliser `*.launch.py` seulement si YAML ne suffit pas
- Garder les fichiers de paramètres séparés des fichiers de lancement

## Règles Python

- Utiliser Python et `rclpy`
- Identifiants en français sans accents
- Commentaires, docstrings et textes utilisateur en français avec accents
- Docstrings multilignes
- Lignes limitées à 100 caractères
- Code lisible, maintenable, sobre et pédagogique
- Respecter les bonnes pratiques Python, sans purisme ni complexité décorative
- Ne pas extraire une méthode ou une fonction si elle ne contient que quelques lignes triviales ;
  préférer alors un commentaire clair dans le flux principal
- Éviter la surconception
- Utiliser constantes, `Enum` ou `dataclass` lorsque cela évite des chaînes littérales dispersées
- Ne pas transformer un script simple en framework
- Ajouter un peu plus de commentaires que la moyenne pour faciliter la relecture, surtout sur
  l’intention, les calculs, les conditions et les logiques non immédiates
- Ne pas commenter trivialement chaque ligne

### Organisation des classes

- Ordonner les méthodes ainsi : `__init__`, méthodes publiques, callbacks regroupées par type,
  méthodes privées utilitaires, méthodes de cycle de vie
- Nommer les callbacks ROS 2 avec un suffixe `_callback`
- Pour les classes assez longues, ajouter des séparateurs visuels sobres :
  `# --- Callbacks des subscriptions ---`, `# --- Callbacks des services ---`,
  `# --- Callbacks des timers ---`, `# --- Méthodes privées utilitaires ---`,
  `# --- Cycle de vie du nœud ---`
- Rédiger les docstrings multilignes en français, à l’indicatif présent, avec une première ligne
  décrivant directement l’objectif
- Aérer le code avec des lignes vides entre les étapes logiques d’une méthode

## Pylance

Le workspace Devastator utilise Pylance surtout pour l’autocomplétion, la navigation et les erreurs
évidentes.

- Ne pas viser une conformité stricte au typage statique Python
- Éviter tout de même le code ambigu : valeurs possiblement `None`, imports inutiles, attributs
  incertains, retours de services non vérifiés
- Ne pas ajouter de complexité uniquement pour satisfaire un typage statique théorique
- Si une erreur Pylance visible est signalée par l’utilisateur, la corriger simplement

## Interface Pico, moteurs et sécurité matérielle

Utiliser la chaîne existante :

`robot_devastator` → `/pico/commande_moteurs` → `interface_pico` → UART → Pico WH → MDD3A → moteurs

Règles :

- Ne pas contourner `interface_pico` sans raison claire
- Utiliser `commun/msg/ConsigneMoteurs`
- Plage moteur : `-1000` à `1000`
- `0` = arrêt
- positif = avancer
- négatif = reculer
- arrêt explicite et fiable obligatoire
- ne jamais corriger un mauvais sens moteur en logiciel ; corriger le câblage moteur au MDD3A

Les tests matériels doivent être courts, progressifs et sécuritaires :

- roues dans le vide pour tout test moteur non validé
- vitesses faibles au début
- arrêt prévu dans tous les tests
- `finally` requis si le code contrôle directement du matériel
- ne jamais lancer d’action destructive ou longue sans accord explicite

## Tests et validation

### Essais en bac à sable

Les nœuds ROS 2 écrivent les logs dans `~/.ros/log`, soit hors zone écrivable du bac à sable.
Pour éviter les échecs de tests, rediriger temporairement les logs ROS vers `/tmp`.

### Validation automatisée ROS 2

- Conserver sans modification les fichiers de tests standards générés par ROS 2
- Ne pas exécuter `pytest` directement dans ce workspace
- Utiliser `colcon test --packages-select <package>` puis `colcon test-result --verbose`

## Documentation

Documenter suffisamment pour faciliter l’usage et la réutilisation sans avoir à lire le code.

Mettre à jour `README.md` si une modification change :

- le lancement
- les topics
- les services
- les paramètres
- la structure
- une procédure de test

Tenir à jour les documents spécialisés si la modification les concerne :

- `docs/architecture_cible.md`
- `docs/connexions.md`
- `docs/parametres.md`
- `docs/inventaire_composantes.md`

Respecter le style et le cadre déjà documentés.

## Git

- Branches simples et ciblées
- Commits petits, fréquents et cohérents
- Messages de commit en français
- Ne jamais faire de `reset`, `merge`, suppression ou déplacement massif sans accord
- Ne pas modifier l’historique Git sans demande explicite

## Interaction avec Codex

Avant une modification non triviale :

1. analyser le code existant ;
2. proposer un plan court ;
3. attendre validation.

Pour chaque tâche :

- partir du code existant
- faire la plus petite modification utile
- indiquer les fichiers touchés
- expliquer comment tester
- éviter les solutions parallèles
