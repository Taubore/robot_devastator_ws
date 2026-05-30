## Architecture directrice

L’architecture du projet doit s’inspirer d’un modèle modulaire par capacités, similaire
dans l’esprit aux modules de type "Robot Skill" de Synthiam ARC, mais adapté à ROS 2
et sans interface graphique.

Objectif architectural :

- construire progressivement une bibliothèque de capacités robotiques réutilisables
- éviter les applications monolithiques difficiles à réutiliser
- isoler les différences entre robots dans des paramètres et fichiers de lancement
- permettre à un module validé sur Devastator d’être réutilisable plus tard sur RobotPi
  ou un autre robot
- garder l’architecture simple, testable et adaptée au niveau actuel du projet

Un module ROS 2 doit représenter une capacité claire du robot :

- lecture d’un capteur
- interface avec un microcontrôleur
- perception simple
- décision simple
- commande de mouvement
- téléopération
- affichage d’état
- voix
- caméra
- lidar
- navigation

Un module ne doit pas connaître inutilement un robot précis. Les différences propres à
Devastator doivent être placées dans :

- des paramètres ROS 2
- des fichiers YAML
- des fichiers `launch.py`
- le package d’intégration du robot

Le code fonctionnel doit rester dans des nœuds ou packages réutilisables. Le code
d’assemblage propre à Devastator doit rester dans le package principal du robot ou dans
un espace de type `bringup` si cette structure devient nécessaire.

### Correspondance architecturale recherchée

Le parallèle conceptuel à respecter est le suivant :

- "Robot Skill" ARC → nœud ou package ROS 2 spécialisé
- configuration d’un skill → paramètres ROS 2 et fichiers YAML
- projet ARC → fichier `launch.py` assemblant les capacités du robot
- communication entre skills → topics, services ou actions ROS 2
- bibliothèque de skills → packages ROS 2 réutilisables du workspace

Il ne faut pas reproduire l’interface graphique de Synthiam ARC. Pour ce projet, la
configuration doit rester textuelle, simple et versionnée dans Git.

### Séparation des responsabilités

Respecter cette séparation autant que possible :

- un nœud capteur lit le matériel ou reçoit une mesure brute
- un nœud perception transforme les mesures en information utile
- un nœud décision choisit une action
- un nœud actionneur applique une commande au matériel
- un fichier `launch.py` assemble les nœuds nécessaires
- un fichier YAML ajuste les paramètres pour un robot donné

Exemple conceptuel pour l’autonomie simple :

- un module mesure les distances
- un module détecte si un obstacle est présent
- un module choisit le côté le plus dégagé
- un module produit ou relaie la commande de déplacement
- `interface_pico` transmet la commande au Pico WH

Éviter les nœuds qui lisent les capteurs, prennent toutes les décisions et commandent
directement les moteurs dans un seul bloc, sauf pour un test temporaire très limité et
explicitement identifié comme tel.

### Interfaces entre modules

Les modules doivent communiquer par interfaces ROS 2 explicites :

- topic pour un flux de données ou une commande continue
- service pour une demande ponctuelle avec réponse immédiate
- action pour une tâche longue, annulable ou suivie dans le temps

Ne pas utiliser d’appels directs entre classes de modules lorsque l’objectif est une
communication entre capacités robotiques. Dans ROS 2, l’interface publique d’un module
doit être un topic, un service, une action ou des paramètres.

Les noms de topics, services, actions et paramètres doivent être simples, stables et
documentés lorsqu’ils deviennent importants pour l’usage du robot.

### Paramétrage

Préférer les paramètres ROS 2 aux valeurs codées en dur pour tout ce qui peut varier
d’un robot à l’autre ou d’un test à l’autre :

- vitesses
- seuils de distance
- temporisations
- ports série
- noms de frame
- inversion logique
- limites de sécurité
- fréquences de publication
- comportement par défaut

Une valeur codée en dur est acceptable seulement si elle est réellement constante,
locale et peu susceptible de varier.

Quand un paramètre influence le comportement physique du robot, choisir une valeur
prudente par défaut.

### Réutilisabilité

Avant d’ajouter une logique dans `robot_devastator`, se demander :

1. Est-ce une capacité propre à Devastator?
2. Est-ce une capacité qui pourrait servir à RobotPi ou à un autre robot?
3. Est-ce un simple assemblage de modules existants?
4. Est-ce une expérimentation temporaire?

Si la capacité est réutilisable, éviter de l’ancrer inutilement dans Devastator.

Si la logique est propre à Devastator, elle peut rester dans `robot_devastator`.

Si la logique sert surtout à assembler plusieurs modules, elle doit être placée dans un
fichier de lancement ou une couche d’orchestration simple.

Si le code est temporaire, le nom du fichier, les commentaires ou la documentation doivent
le rendre évident.

### Niveau d’abstraction souhaité

L’architecture doit être modulaire, mais pas bureaucratique.

À éviter :

- créer un framework maison
- créer trop de petits packages artificiels
- multiplier les abstractions avant validation physique
- créer des interfaces génériques non utilisées
- préparer des intégrations futures au lieu de terminer l’objectif actuel

À viser :

- un module clair par capacité utile
- une interface ROS 2 explicite
- des paramètres ajustables
- un test simple
- une documentation courte
- une validation physique progressive

Règle pratique :

Une capacité claire et réutilisable peut devenir un module. Une simple fonction locale
ne doit pas devenir un module uniquement pour respecter une architecture théorique.

### Évolution progressive

L’architecture doit évoluer par étapes validées :

1. rendre le comportement actuel fiable
2. isoler les responsabilités évidentes
3. paramétrer ce qui doit varier
4. documenter les interfaces utiles
5. réutiliser seulement ce qui a été validé
6. extraire un module générique seulement lorsque le besoin est réel

Ne pas refactoriser massivement pour atteindre une architecture idéale d’un seul coup.
Le projet doit rester exécutable et testable après chaque étape.

### Rôle de Codex dans l’architecture

Pour toute modification touchant l’architecture, Codex doit :

1. analyser la structure existante
2. identifier si le changement est local, modulaire ou transversal
3. proposer le plus petit changement architectural utile
4. préserver la compatibilité avec la chaîne existante
5. éviter les duplications de logique
6. indiquer clairement les fichiers touchés
7. expliquer comment tester
8. signaler les impacts sur `README.md`, topics, services, paramètres ou launch files

Codex ne doit pas créer de nouveau package, nouveau message, nouveau service ou nouvelle
structure de type `bringup` sans justification claire.

Toute extraction vers un module réutilisable doit être motivée par un besoin réel, pas par
une recherche d’architecture parfaite.