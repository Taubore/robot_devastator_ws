# Décisions et leçons — Devastator

Ce document rassemble ce qui reste vrai et utile dans la durée : les choix techniques durables et leur justification, ainsi que les pièges déjà rencontrés et leur solution, réutilisables sur RobotPi ou un projet futur. Aucun statut ponctuel ici (« test réussi le X ») — seulement ce qui reste valable après plusieurs mois. Demeure synthèse dans les explications, mais ne pas omettre de choses importantes à mémoriser pour le futur. Ce document est utile notamment pour ne pas refaire les mêmes erreurs dans le cadre d'un autre projet, mais aussi pour se rafraîchir la mémoire au cas où un problème se reproduit et qu'on a oublié la solution. Il faut donc que le problème soit suffisamment bien décrit avec son contexte, mais en demeurant synthèse.

Chaque leçon suit le même canevas : **Contexte / symptôme** (comment le problème se manifeste), **Cause**, **Solution retenue**, **À retenir** (ce qui se réutilise ailleurs). Les leçons sont regroupées par domaine.

## Décisions techniques

### Correction du sens moteur au câblage

Le moteur gauche est inversé physiquement au niveau du MDD3A (inversion des deux fils d'entrée sur le bornier), plutôt que de compenser son sens de rotation dans le code. Objectif : garantir que la même convention logique s'applique aux deux moteurs (`avancer()` fait avancer, `reculer()` fait reculer des deux côtés), sans code spécial par moteur.

### Audio purement décoratif

L'audio (annonces via `annonces_audio`) reste une capacité informative, jamais requise pour la sécurité ou le fonctionnement du robot. Conséquence : un défaut audio (clac, device absent) ne justifie pas un chantier prioritaire.

### Ne jamais modifier un paquet externe : encapsuler dans un nœud dédié

Les paquets tiers (`rplidar_ros`, Piper) ne sont jamais modifiés. Tout comportement à adapter passe par un nœud pont dédié (`gestion_lidar` pour le RPLIDAR), qui expose une interface simple au reste du système. Voir « Démarrage automatique du RPLIDAR » pour la justification et la dette technique associée.

### Simulation Gazebo isolée

La simulation est lancée via `diag_simulation.launch.yaml`, avec une `GZ_PARTITION` dédiée et `GZ_IP=127.0.0.1`, pour qu'elle ne puisse pas se mélanger à une autre session ni à une interface réseau parasite. Voir « Serveur Gazebo orphelin ».

## Leçons apprises

### Matériel, alimentation et mécanique

#### Blocage de chenilles — mode de défaillance récurrent

**Contexte / symptôme** : une ou les deux chenilles s'immobilisent alors qu'une consigne moteur non nulle est maintenue (obstacle infranchissable, coincement contre un mur, objet pris dans le barbotin, sol trop adhérent en rotation sur place). Le moteur reste sous tension, rotor bloqué.

**Cause** : inhérente à la mécanique de la plateforme (chenilles plastique, deux moteurs FIT0521 6 V, entraînement direct sans limiteur de couple). À considérer comme un comportement attendu, pas comme un incident exceptionnel.

**Conséquences observées** :

- **Courant maximal du robot** : les deux chenilles bloquées à consigne 1000 tirent environ 6,5 A sur le rail moteur, contre ~0,5 A en rotation libre et ~1,25 A en charge partielle (voir « Consommation du robot » dans [README.md](../README.md)). C'est le pire cas de consommation.
- **Échauffement du câblage de masse** : un blocage prolongé a déjà provoqué un échauffement visible du câblage de masse du rail moteur. Un fusible rapide 10 A / 20 mm a été ajouté sur le positif du rail moteur en réponse (voir [parametres.md](parametres.md)).
- **Odométrie faussée** : les encodeurs cessent de compter alors que le robot « pousse » ; toute pose accumulée pendant un blocage est fausse.

**Détection** : `surveillance_alimentation` publie le courant du rail moteur sur `/alimentation/moteur` (`sensor_msgs/BatteryState`, champ `current`). Un courant qui reste élevé (> ~3 A) alors que les encodeurs ne bougent pas est la signature d'un blocage. Aucune détection automatique n'existe : cette entrée sert de repère pour l'interprétation manuelle et pour une éventuelle protection logicielle.

**À retenir** :

- Ne pas insister sur une consigne quand le robot ne bouge plus : couper la consigne (arrêt clavier, `Ctrl+C`, ou `/pico/stop_moteurs`).
- Après un blocage prolongé, vérifier la température du câblage de masse et l'état du fusible avant de repartir.
- Un blocage pendant un parcours de validation d'odométrie invalide la mesure de dérive : reprendre le test.
- En navigation (SLAM + Nav2), la pose dérive brutalement et la carte se désaligne en cas de blocage : le comportement de récupération Nav2 doit être réglé et testé explicitement sur cette plateforme, et la surconsommation surveillée via `surveillance_alimentation`. Tout écart d'odométrie soudain est un blocage possible.

#### Démarrage du Pico WH perturbé par la TX du Raspberry Pi

**Contexte / symptôme** : le Pico WH ne démarre pas (ou démarre mal) dans certaines configurations de branchement, sans que le code soit en cause.

**Cause** : ni l'USB seul ni le Pico seul. La ligne critique est Raspberry Pi TX GPIO14 → Pico RX GP1 : la TX du Pi 4, active pendant le boot du Pico, perturbe son démarrage. Observations : Pico seul OK ; Pico avec fil GP1 seul OK ; Pico avec Pi4 éteint relié à GP1 OK ; Pico avec Pi4 allumé relié à GP1 KO.

**Solution retenue** (règle de travail) :

- **Mode développement Pico par USB** : USB branché au Pico, déconnecter au minimum la ligne Pi TX GPIO14 → Pico RX GP1. La ligne Pico TX GP0 → Pi RX GPIO15 peut rester en place.
- **Mode test avec Raspberry Pi 4** : USB PC débranché du Pico, Pico alimenté en autonome via VSYS, UART Pi ↔ Pico rebranché complètement, tests via `/dev/ttyS0`.
- **Séquence pratique** : pour développer sur le Pico, débrancher Pi4 TX → Pico RX ; pour tester la communication avec le Pi 4, rebrancher cette ligne, alimenter le Pico via VSYS, puis tester depuis le Pi 4.

**À retenir** : un GPIO d'un hôte actif peut empêcher le boot d'un microcontrôleur relié à lui. Isoler les branchements un par un (composant seul, câble seul, hôte éteint, hôte allumé) pour trouver la ligne fautive.

#### Démarrage automatique du RPLIDAR — comportement matériel non configurable

**Contexte / symptôme** : le RPLIDAR A1M8 tourne dès l'alimentation du robot, avant même le lancement de ROS 2, et le nœud `rplidar_composition` envoie de toute façon sa propre commande de démarrage (log `rplidar_composition: Start`).

**Cause** : comportement matériel documenté dans le datasheet Slamtec (« System connection » : « After power on each sub-system, RPLIDAR A1 start rotating and scanning »). Ce n'est pas un défaut du driver, et aucun paramètre du protocole ne permet de changer cette valeur par défaut à la source.

**Solution retenue** : le nœud pont `gestion_lidar` force la dormance au démarrage du programme (`/stop_motor`, qui coupe le moteur ET le laser, confirmé par l'absence totale de publication sur `/scan`) et expose `activer_lidar` / `desactiver_lidar` à toute source de commande (clavier aujourd'hui, mode automatique ou Nav2 plus tard).

**À retenir** :

- Ce patron (nœud pont dédié au cycle de vie d'un composant externe, plutôt que de loger cette logique dans le premier nœud consommateur) est à réutiliser pour tout composant à comportement matériel autonome. RealSense et ReSpeaker partagent potentiellement le même risque de démarrage non supervisé.
- Dette technique : le patron ROS 2 canonique est `rclcpp_lifecycle` (`configure` / `activate` / `deactivate`). Le paquet officiel `rplidar_ros` (apt) ne l'implémente pas, il n'expose que des services propriétaires (`/stop_motor`, `/start_motor`) ; `gestion_lidar` est une solution pragmatique adaptée à ce paquet. Si un driver RPLIDAR lifecycle-natif devient mûr, réévaluer si `gestion_lidar` peut être simplifié ou remplacé.

#### Arrêt du RPLIDAR à la fermeture : le moteur repart à la fermeture du port série

**Contexte / symptôme** : à `Ctrl+C` sur `devastator.launch.yaml`, le RPLIDAR s'arrête brièvement puis repart, et reste en rotation après la fin complète du lancement.

**Cause (matérielle, confirmée par test)** : sur le RPLIDAR A1, le moteur n'est pas commandé par le protocole série mais par la ligne DTR de l'adaptateur USB-série CP2102 (`MOTOCTL`). Dans le SDK Slamtec, `stopMotor()` asserte DTR et `startMotor()` le relâche. Linux abaisse DTR et RTS à la dernière fermeture du port : la simple sortie de `rplidar_composition` relâche donc DTR et remet le moteur en marche. Aucune commande ROS ne peut l'empêcher, puisque le phénomène se produit quand le driver n'existe plus.

**Pistes écartées** :

1. **Course de signaux.** `ros2 launch` envoie SIGINT à tous les nœuds à peu près en parallèle, et `rplidar_composition` (C++) détruit ses services plus vite que `gestion_lidar` (Python) ne remarque le signal ; l'appel final `/stop_motor` échouait alors après le délai maximal. Un séquencement explicite (gestionnaire `OnShutdown` dans un `.launch.py` dédié) a été essayé puis retiré : complexité réelle sans bénéfice observé. Réduire le délai de réveil du spin de `gestion_lidar` à 0.05 s suffit à gagner la course (appel final en ~16 ms). Ce n'était de toute façon pas la cause du redémarrage.
2. **Redémarrage par le driver.** Le log de fermeture ne montre aucun `rplidar_composition: Start` : le driver ne relance pas le moteur.
3. **Asserter DTR puis fermer proprement le port.** Testé sur le Pi 4 robot arrêté (ouverture du port en Python, `serial.Serial(PORT, 115200).dtr = True`, désactivation de `HUPCL` via `termios` avant fermeture). DTR asserté : le moteur s'arrête et reste arrêté tant que le port est tenu ouvert (preuve que la commande passe par DTR). Port fermé, même avec `HUPCL` désactivé : le moteur repart aussitôt, car le pilote `cp210x` désactive l'interface UART du CP2102 à la fermeture (`CP210X_IFC_ENABLE` / `UART_DISABLE`), ce qui réinitialise les lignes de contrôle quoi qu'en dise termios. Invalidé, ne pas y revenir.

**Solution retenue** : accepter la limite et retirer l'appel `/stop_motor` de fermeture de `gestion_lidar`. Il n'apportait rien (la fermeture du port l'annule) et loguait « RPLIDAR arrêté avant fermeture » alors que le moteur repartait : un log faussement rassurant est pire que pas de log. Le RPLIDAR tourne donc entre deux sessions, jusqu'à la coupure d'alimentation. Deux voies restent possibles si cela devient gênant : un processus « garde-port » qui tient le port ouvert avec DTR asserté (fonctionnerait, mais il faut le tuer avant chaque relance ; complexité disproportionnée), ou couper l'alimentation du RPLIDAR par relais commandé, seule solution réellement propre.

**À retenir** :

- Avant de soupçonner l'ordre des signaux ou le code d'un driver, vérifier quelle couche commande réellement l'actionneur : ici ni ROS ni le protocole série, mais une broche du convertisseur USB.
- Un état porté par une ligne de contrôle modem ne survit pas à la fermeture du port.
- Un actionneur dont l'état dépend d'un processus vivant ne peut pas être garanti après l'arrêt de ce processus ; si la garantie compte, elle doit venir du matériel (relais, rail commutable).

### Perception et odométrie

#### Écart théorie/empirique des ticks par mètre (chenilles)

**Contexte / symptôme** : la valeur théorique de ticks par mètre (calculée à partir du diamètre primitif des chenilles) diffère d'environ 11 % de la valeur mesurée sur le robot réel.

**Cause** : glissement des chenilles plastique sur sol dur, inhérent au type de terrain, pas une erreur de mesure.

**À retenir** : pour tout calcul d'odométrie, les valeurs mesurées empiriquement sur le robot réel priment sur les valeurs théoriques tirées de la géométrie, qui ne servent que de repère de cohérence. Les valeurs actives sont dans `robot_devastator_bringup/config/mecanique.yaml` ; la méthode et le contexte de mesure sont dans [parametres.md](parametres.md).

#### Une calibration insuffisamment répétée fige du bruit en erreur systématique

**Contexte / symptôme** : une constante de calibration (ticks/mètre gauche/droite) établie sur trop peu de passes se comporte comme un biais physique alors qu'elle reflète du bruit de mesure.

**Cause** : le bruit d'une mesure isolée est inscrit dans la configuration comme s'il était reproductible.

**À retenir** : avant d'inscrire une valeur de calibration, vérifier qu'elle repose sur un signal reproductible sur plusieurs passes. Exemple concret : `src/odometrie/README.md`, section « Validation Phase 6 ».

#### Qualité du scan RPLIDAR A1M8 — zones mortes environnementales, pas défaut du capteur

**Contexte / symptôme** : à fréquence stable (~6,8 Hz), le scan sur `/scan` présente des trous persistants même après cumul de plusieurs tours complets (RViz, Decay Time élevé).

**Test décisif** : déplacer le robot dans la pièce et comparer les trous par rapport à l'angle du robot et par rapport à la géométrie de la pièce. La plupart des trous restent liés à des points fixes de la pièce (angles de mur rasants, surfaces peu réfléchissantes), pas à un secteur angulaire fixe du robot.

**Conclusion** : aucun obstacle du châssis ne masque le lidar ; comportement normal d'un capteur bas de gamme en environnement réel, pas un défaut d'intégration.

**À retenir** : ne pas attribuer des trous de scan au câblage ou à un mauvais TF sans d'abord faire ce test de déplacement. Pour SLAM, ces trous persisteront : `slam_toolbox` doit les tolérer par fusion multi-scans plutôt que de les traiter comme des erreurs de mesure.

### Audio

#### Bruit de démarrage (« clac ») de l'ampli I2S

**Contexte / symptôme** : l'ampli I2S (MAX98357 + PCM5102A) produit un clac audible au début de chaque lecture séparée.

**Cause probable** : l'ouverture et la fermeture du flux audio par `aplay`, pas le routage GPIO ni `dtparam=audremap`.

**Pistes essayées sans succès** : `audremap`, lecture en flux continu, tentative via SD/shutdown, pré-silence ou fade-in dans les WAV.

**Décision** : chantier abandonné pour l'instant (audio décoratif). Pistes si le besoin redevient prioritaire : lecteur audio persistant, ou solution matérielle anti-pop.

#### Résolution du device ALSA « default » — instabilité entre redémarrages

**Contexte / symptôme** : `annonces_audio` (paramètre `aplay -D default`) échoue soudain avec `aplay: audio open error`, alors qu'aucun câblage ni code audio n'a changé.

**Cause** : la résolution de `default` dépend de l'ordre d'énumération des cartes son au démarrage du noyau. Un changement dans les périphériques USB présents (notamment le branchement du RPLIDAR, interface série USB) décale cet ordre et peut faire basculer `default` vers une autre carte (par exemple la sortie HDMI `vc4hdmi0`, sans device réel à l'écoute).

**Correction abandonnée** : fixer `default` sur l'index numérique de la carte HifiBerry (`defaults.pcm.card 1`). Instable elle aussi : le même mécanisme déplace l'index attribué à `sndrpihifiberry`, et le bris est revenu quelques jours plus tard.

**Solution retenue** : cibler la carte par son nom stable (`sndrpihifiberry`, dérivé du pilote, indépendant de l'ordre d'énumération) via `/etc/asound.conf` :

``` bash
pcm.!default {
    type plug
    slave.pcm {
        type hw
        card sndrpihifiberry
    }
}
ctl.!default {
    type hw
    card sndrpihifiberry
}
```

Le bloc `type plug` est nécessaire : un accès direct (`type hw`) par nom a échoué avec `Channels count non available`, faute de la conversion automatique de format/canaux que `plug` fournit.

**À retenir** : ne jamais utiliser d'index numérique de carte dans une configuration ALSA sur ce Pi, toujours résoudre par nom (`cat /proc/asound/cards` pour confirmer). Revérifier `aplay -l` et `/etc/asound.conf` après tout ajout ou retrait de périphérique USB, avant de conclure à un problème logiciel côté `annonces_audio`.

### Lancement ROS 2 et intégration

#### Un nœud validé manuellement peut rester absent du lancement de production sans le signaler

**Contexte / symptôme** : `robot_state_publisher` avait été lancé manuellement en test depuis la Phase 8 (package `robot_devastator_description`, `affichage.launch.py` / `simulation.launch.py`) sans jamais être intégré à `devastator.launch.yaml`, le lancement de production. Au démarrage normal, `/tf_static` n'était jamais publié. Rien ne signalait l'oubli, car aucun nœud de production n'en dépendait. Le problème n'est apparu qu'en Phase 9, avec le RPLIDAR et le frame `laser_link` : RViz ne pouvait pas résoudre les frames fixes, alors que la visualisation manuelle fonctionnait (elle lance `robot_state_publisher` elle-même).

**Solution retenue** : ajouter `robot_state_publisher` au lancement de production (voir la leçon suivante pour la forme exacte, `robot_devastator_bringup/README.md` pour le détail).

**À retenir** : un nœud fondamental (TF, description du robot, etc.) validé en lancement de diagnostic ou manuel doit être ajouté à `devastator.launch.yaml` dès que son usage devient permanent, même si aucun autre nœud n'en dépend encore. Vérifier explicitement la couverture du lancement de production à chaque nouvelle intégration de capteur ou de frame TF.

#### La typographie française « mot : mot » dans un xacro casse l'inférence de type YAML de launch_yaml

**Contexte / symptôme** : charger un `robot_description` via `$(command 'xacro ...')` comme `value:` d'un `param` dans un `*.launch.yaml` fait échouer `ros2 launch` avec `Failed to convert '<contenu XML>' using yaml rules: yaml.safe_load() failed — mapping values are not allowed here`. L'erreur pointe la ligne d'un commentaire français du XML généré (ex. `<!-- Matériaux : définis une seule fois... -->` dans `corps.xacro`), pas une vraie erreur de syntaxe du xacro.

**Cause** : `launch_yaml` passe le résultat de la substitution par `yaml.safe_load()` pour déduire le type du paramètre ; le motif « mot espace deux-points espace mot » est interprété à tort comme une clé de mapping YAML.

**Solution retenue** : sortir `robot_state_publisher` dans un `robot_state_publisher.launch.py` dédié qui traite le xacro en Python (`xacro.process_file(...).toxml()`) et le passe dans le dictionnaire de paramètres du `Node` (valeur déjà typée `str`, pas d'inférence). Ce fichier est inclus depuis `devastator.launch.yaml` par une action `include`, ce qui préserve un point d'entrée de production unique. Voir `robot_devastator_bringup/README.md`.

**À retenir** : tout `param` chargé dynamiquement par `$(command ...)` dans un `*.launch.yaml` (ou `.xml`) est à risque si le contenu généré peut contenir du texte français avec espace avant deux-points (commentaires XML, chaînes de configuration, messages générés). Isoler alors le nœud dans un `*.launch.py` minimal et l'inclure, plutôt que de reformuler la typographie des commentaires sources pour contourner un détail d'implémentation.

### Simulation Gazebo

#### Serveur Gazebo orphelin : modèle figé et plantage

**Contexte / symptôme** : Gazebo affichait toujours la même version du modèle malgré les modifications du xacro, alors que RViz reflétait correctement les changements. Un plantage `getenv` dans le fil de découverte de gz-transport est aussi apparu.

**Cause confirmée** : un processus `gz sim server` d'une session antérieure (PID bas, détaché de tout terminal) tournait encore ; chaque nouveau lancement dialoguait avec ce serveur et son modèle périmé. Origine probable, non confirmée : une simulation lancée en arrière-plan par Claude Code et jamais arrêtée.

**Cause probable, non prouvée** : le plantage `getenv` découle de la cohabitation de deux serveurs. Gazebo publiait aussi sur l'interface Tailscale (plusieurs interfaces réseau actives), ce qui fragilise sa découverte.

**Diagnostic** :

- RViz correct mais Gazebo figé : soupçonner Gazebo, pas le xacro.
- Avant le launch, `gz topic -l` doit être vide ; sinon un serveur orphelin tourne.
- `gz topic -i -t /clock` donne l'adresse du publieur ; `pgrep -af "gz|ruby"` donne le PID.
- Un statut « process has finished cleanly » ne prouve pas le bon fonctionnement.

**Solution retenue** : isoler la simulation dans `diag_simulation.launch.yaml` (`GZ_PARTITION` dédiée, `GZ_IP=127.0.0.1`).

**Leçons de méthode** :

- Lire le diff d'une modification faite par Claude Code avant de lancer un test complet.
- Pour isoler une modification, mettre de côté tous les fichiers modifiés ensemble, pas un seul : un état partiel produit des symptômes trompeurs.
- Ne jamais laisser une simulation en arrière-plan sans l'arrêter.

#### Topic du capteur simulé vs topic du pont : deux déclarations indépendantes

**Contexte / symptôme** : `/scan` silencieux (aucun message, aucune erreur) alors que le xacro, les couleurs, la géométrie et le pont étaient corrects. `gz topic -l` montrait pourtant `/scan` et `/scan/points` actifs côté Gazebo.

**Cause confirmée** : le capteur (`devastator_gazebo.xacro`) publie sur le nom de sa balise `<topic>` (ici `scan` → `/scan`), alors que le pont (`gazebo_bridge.yaml`) écoutait le nom composé par défaut (`.../link/laser_link/sensor/rplidar/scan`), utilisé uniquement en l'absence de `<topic>` explicite. Les deux déclarations sont indépendantes et rien ne les valide l'une contre l'autre : le pont se crée sans erreur même s'il écoute un topic inexistant.

**Diagnostic décisif** : `gz topic -e -t <nom exact de gz_topic_name>` restait muet alors que `gz topic -l` confirmait la publication. Comparer `gz topic -l` au `gz_topic_name` du fichier de pont, plutôt que de chercher côté capteur, xacro ou GPU.

**Fausse piste** : le rendu GPU/EGL (`libEGL warning: failed to create dri2 screen`) sur portable hybride Intel/NVIDIA. Cet avertissement est bénin (présent dans plusieurs rapports de bogue officiels Gazebo sans empêcher le rendu). `prime-select nvidia` reste une bonne pratique générale sur ce type de machine.

**À retenir** : quand un capteur avec `<topic>` explicite est ponté vers ROS 2, vérifier que `gz_topic_name` du `.yaml` correspond exactement à ce topic, pas au nom composé par défaut. Piège classique en copiant un bloc de pont d'un capteur sans `<topic>` déclaré.
