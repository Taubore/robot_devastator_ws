# AGENTS.md — Consignes pour Codex

## Projet

Devastator est un robot mobile réel servant de plateforme d’apprentissage en électronique,
robotique, Python, ROS 2 et systèmes embarqués.

Dépôt officiel : https://github.com/Taubore/robot_devastator_ws

Ce dépôt est le workspace ROS 2 officiel du projet. Il existe déjà et doit évoluer
progressivement. Ne pas créer d’architecture parallèle et ne pas repartir de zéro.

## Environnements

Le projet utilise deux environnements complémentaires.

### Legion-Linux

Environnement principal de développement.

- Ordinateur Lenovo Legion Pro 5 16IRX9 Type 83DF, Intel Core i7-14650HX, 32 Go RAM, NVIDIA GeForce RTX 4060 Laptop GPU avec 8 Go VRAM
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
- M'aviser s'il est préférable d'installer de nouvelles bibilothèques ou composantes dans un venv

## Structure existante

Respecter la structure ROS 2 existante.

- `src/commun` : interfaces ROS 2 communes
- `src/interface_pico` : interface ROS 2 entre Raspberry Pi 4 et Pico WH
- `src/robot_devastator` : logique principale du robot

Avant d’ajouter un fichier ou un package, vérifier si le besoin peut être couvert par le code
existant. Toute évolution d’architecture non triviale doit être proposée avant modification.

Ne pas créer une architecture parallèle. L’évolution doit se faire par extraction progressive
de responsabilités claires à partir du code existant, en conservant un robot fonctionnel à
chaque étape.

## Architecture directrice

L’architecture doit s’inspirer du modèle modulaire de Synthiam ARC : un robot est un
assemblage de capacités indépendantes, configurables et réutilisables.

Dans ROS 2, cela signifie :

- une capacité claire = un nœud ou package ROS 2 spécialisé
- configuration = paramètres ROS 2 et fichiers YAML
- assemblage du robot = fichiers `launch`, préférablement `*.launch.yaml`
- communication entre capacités = topics, services ou actions
- réutilisation = modules non liés inutilement à Devastator

Ne pas créer une application monolithique. Ne pas créer non plus un framework maison.

Les différences propres à Devastator doivent rester dans les paramètres, les fichiers YAML,
les fichiers `launch.py` ou la couche d’assemblage du robot.

Un module réutilisable ne doit pas connaître inutilement le robot précis qui l’utilise.

Séparation souhaitée :

- capteur : lit ou publie une mesure
- perception : transforme les mesures en information utile
- décision : choisit une action
- actionneur : applique une commande au matériel
- lancement : assemble les modules

Règle pratique :

Extraire une capacité en module seulement lorsqu’elle est claire, utile et testable. Ne pas
refactoriser massivement pour atteindre une architecture idéale. Le robot doit rester
exécutable et testable après chaque étape.

Les détails et exemples d’architecture modulaire peuvent être documentés dans
`docs/architecture_modulaire.md`. `AGENTS.md` reste la référence courte et prioritaire pour
guider Codex.

## Objectif fonctionnel actuel

L’objectif court terme du projet est une autonomie simple du robot :

1. avancer lentement
2. détecter un obstacle devant
3. s’arrêter
4. comparer gauche et droite
5. tourner vers le côté le plus dégagé
6. reprendre l’avance

Plusieurs intégration de matériel sont pour le futur et ne doivent pas être intégrés maintenant, par contre il est important de le savoir pour s'assurer d'une saine évolution vers cette cible. 
- La voix en français via Piper (une intégration est déjà amorcée, mais pas achevée).
- Encodeur en quadrature montés sur les moteurs DFRobot FIT0521 (à connecter via interface_pico).
- Manette PS2 pour effectuer de la téléopération lorsque ce sera aidant pour les tests.
- Module Waveshare LCD 2" ST7789V pour visage du robot et aussi mode état du robot en plusieurs pages.
- Slamtec RPLIDAR A1M8.
- Camera RealSense D435IF.
- ReSpeaker Mic Array v3.0 de SeeedStudio pour réception vocale

## Principe de progression

Appliquer la règle suivante : une seule complexité à la fois, validée physiquement.

Donc :

- pas d’intégration prématurée
- pas de capteur avant validation moteur
- pas de PID avant mesures fiables
- pas de caméra, lidar ou perception avancée à cette étape
- tests réels simples avant abstraction

Quant à la l'architecture directrice, il s'agit d'appliquer les principes de module seulement quand une responsabilité est claire, testable et susceptible d’être réutilisée. Autrement, il ne faut pas appliquer cette architecture dès le départ, car cela ralentira la progression de l'humain dans son projet plutôt que de l'aider.

## Règles Git

- Branches simples et ciblées
- Commits petits, fréquents et cohérents
- Messages de commit en français
- Ne jamais faire de `reset`, `merge`, suppression ou déplacement massif sans accord
- Mettre à jour `README.md` si le lancement, la structure ou le comportement change

## Règles Python

- Utiliser Python et `rclpy`
- Identifiants en français sans accents
- Commentaires, docstrings et textes utilisateur en français avec accents
- Docstrings multilignes
- Lignes limitées à 100 caractères
- Code lisible, maintenable, sobre et pédagogique
- Éviter la surconception
- Utiliser constantes, `Enum` ou `dataclass` lorsque cela évite des chaînes littérales dispersées
- Ne pas transformer un script simple en framework

## Pylance

Le workspace Devastator utilise Pylance surtout pour l’autocomplétion, la navigation et les erreurs évidentes.

- Ne pas viser une conformité stricte au typage statique Python.
- Éviter tout de même le code ambigu : valeurs possiblement `None`, imports inutiles, attributs incertains, retours de services non vérifiés.
- Ne pas ajouter de complexité uniquement pour satisfaire un typage statique théorique.
- Si une erreur Pylance visible est signalée par l’utilisateur, la corriger simplement.

## Règles ROS 2

- Respecter les conventions ROS 2 Jazzy
- Utiliser les messages et services existants quand ils suffisent
- Ne pas créer de nouveaux `.msg` ou `.srv` sans nécessité claire
- Préférer les paramètres ROS 2 aux valeurs codées en dur
- Les nœuds doivent être lançables depuis VSCode ou via `ros2 launch`.
- Éviter les longues séquences CLI sauf diagnostic, installation ou build nécessaire
- Utiliser les topics pour les flux continus de données ou de commandes
- Utiliser les services pour les demandes ponctuelles
- Utiliser les actions pour les comportements longs, annulables ou suivis
- Documenter les interfaces ROS 2 lorsqu’elles deviennent des points d’intégration stables
- Garder les différences entre robots dans les paramètres YAML et les fichiers launch
- Regrouper les lancements complets du robot dans le package `robot_devastator_bringup`
  lorsque plusieurs nœuds, paramètres ou sous-systèmes doivent être assemblés.
- Préférer les fichiers `*.launch.yaml` pour les lancements simples.
- Utiliser `*.launch.py` seulement si YAML ne suffit pas : logique conditionnelle,
  génération dynamique, besoin ROS 2 non exprimable proprement en YAML ou logique de lancement devient trop complexe pour rester clair.
- Garder les fichiers de paramètres séparés des fichiers de lancement, même si les deux
  utilisent YAML (`robot_devastator_bringup/config` ou `robot_devastator_bringup/launch`).

## Interface Pico et moteurs

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

Ne jamais corriger un mauvais sens moteur en logiciel. Corriger le câblage moteur au MDD3A.

## Tests matériels

Les tests matériels doivent être courts, progressifs et sécuritaires.

- Roues dans le vide pour tout test moteur non validé
- Vitesses faibles au début
- Arrêt prévu dans tous les tests
- `finally` requis si le code contrôle directement du matériel
- Ne jamais lancer d’action destructive ou longue sans accord explicite

## Documentation

Documenter seulement ce qui aide réellement, mais sans oublier que l'utilisateur est débutant en programmation Python et en ROS 2. Donc, commenter un peu plus que si c'était un programme fait pour des professionels.

Mettre à jour `README.md` si une modification change :

- le lancement
- les topics
- les services
- les paramètres
- la structure
- une procédure de test

## Essais en bac à sable
- Les noeuds ROS 2 écrivent les logs dans ~/.ros/log, soit hors zone écrivable du bac à sable. Pour que les tests n'échouent pas, il faut rediriger temporairement les logs ROS vers /tmp.

## Validation automatisée ROS 2

- Conserver sans modification les fichiers de tests standards générés par ROS 2.
- Ne pas exécuter `pytest` directement dans ce workspace.
- Utiliser `colcon test --packages-select <package>` puis `colcon test-result --verbose`.

## Interaction avec Codex

Avant une modification non triviale :

1. analyser le code existant
2. proposer un plan court
3. attendre validation

Pour chaque tâche :

- partir du code existant
- faire la plus petite modification utile
- indiquer les fichiers touchés
- expliquer comment tester
- éviter les solutions parallèles
