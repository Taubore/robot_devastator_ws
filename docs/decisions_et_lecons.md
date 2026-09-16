# Décisions et leçons — Devastator

Ce document rassemble ce qui reste vrai et utile dans la durée : les choix
techniques durables et leur justification, ainsi que les pièges déjà
rencontrés et leur solution, réutilisables sur RobotPi ou un projet futur.
Aucun statut ponctuel ici (« test réussi le X ») — seulement ce qui reste
valable après plusieurs mois.

## Décisions techniques

### Correction du sens moteur au câblage

Le moteur gauche est inversé physiquement au niveau du MDD3A (inversion des
deux fils d'entrée sur le bornier), plutôt que de compenser son sens de
rotation dans le code. Objectif : garantir que la même convention logique
s'applique aux deux moteurs (`avancer()` fait avancer, `reculer()` fait
reculer des deux côtés), sans code spécial par moteur.

## Leçons apprises

### Blocage de chenilles — mode de défaillance connu

Le blocage de chenilles est un mode de défaillance **récurrent** de la
plateforme Devastator, inhérent à sa mécanique (chenilles plastique, deux
moteurs FIT0521 6 V, entraînement direct sans limiteur de couple). Il faut
le considérer comme un comportement attendu de la plateforme, pas comme un
incident exceptionnel.

#### Description

Une ou les deux chenilles se retrouvent immobilisées alors qu'une consigne
moteur non nulle est maintenue : obstacle infranchissable, coincement
contre un mur, objet pris dans le barbotin, sol trop adhérent en rotation
sur place. Le moteur reste sous tension, à rotor bloqué.

#### Conséquences observées

- **Courant maximal du robot.** Les deux chenilles bloquées à consigne 1000
  tirent environ **6,5 A** sur le rail moteur, contre ~0,5 A en rotation
  libre et ~1,25 A en charge partielle (voir la section « Consommation du
  robot » du [README.md](../README.md)). C'est le pire cas de consommation
  de la plateforme.
- **Échauffement du câblage de masse.** Un blocage prolongé a déjà provoqué
  un échauffement visible du câblage de masse du rail moteur. Un **fusible
  rapide 10 A / 20 mm** a été ajouté sur le positif du rail moteur en
  réponse (voir [parametres.md](parametres.md)).
- **Odométrie faussée.** Les chenilles bloquées ne tournent plus mais les
  moteurs peuvent patiner ou vibrer : les encodeurs cessent de compter
  alors que le robot « pousse ». Toute estimation de pose accumulée pendant
  un blocage est fausse.

#### Impact sur les phases futures

- **Phase 6 (odométrie réelle) :** un blocage pendant un parcours de
  validation invalide la mesure de dérive. Reprendre le test.
- **Phase 10 (SLAM + Nav2) :** les parcours de navigation seront faussés
  par les blocages — la pose estimée dérive brutalement, la carte se
  désaligne. Le comportement de récupération Nav2 (« robot bloqué ? »)
  devra être réglé et testé explicitement sur cette plateforme, et la
  surconsommation associée surveillée via `surveillance_alimentation`.

#### Détection

`surveillance_alimentation` publie le courant du rail moteur sur
`/alimentation/moteur` (`sensor_msgs/BatteryState`, champ `current`). Un
courant moteur qui reste élevé (> ~3 A) alors que les encodeurs ne bougent
pas est la signature d'un blocage. Aucune détection automatique n'est
implémentée à ce jour : cette entrée sert de repère pour l'interprétation
manuelle et pour une éventuelle protection logicielle ultérieure.

#### Conduite à tenir

- Ne pas insister sur une consigne moteur quand le robot ne bouge plus :
  couper la consigne (arrêt clavier, `Ctrl+C`, ou `/pico/stop_moteurs`).
- Après un blocage prolongé, vérifier la température du câblage de masse
  du rail moteur et l'état du fusible avant de repartir.
- En phase de navigation, considérer tout écart d'odométrie soudain comme
  un blocage possible.

### Piège de démarrage du Pico WH — TX du Raspberry Pi active pendant le boot

Le problème de démarrage observé n'est causé ni par l'USB seul ni par le
Pico seul : la ligne réellement critique est Raspberry Pi TX GPIO14 → Pico
RX GP1.

Comportement observé :

- Pico seul : démarrage OK.
- Pico avec fil GP1 seul : démarrage OK.
- Pico avec Pi4 éteint relié à GP1 : démarrage OK.
- Pico avec Pi4 allumé relié à GP1 : démarrage KO.

Conclusion : la TX du Raspberry Pi 4 perturbe le démarrage du Pico lorsqu'elle
est reliée au RX GP1 pendant le boot du Pico.

Règle de travail qui en découle :

- **Mode développement Pico par USB** : USB branché au Pico, déconnecter au
  minimum la ligne Raspberry Pi TX GPIO14 → Pico RX GP1. La ligne Pico TX
  GP0 → Raspberry Pi RX GPIO15 peut rester en place si elle ne perturbe pas
  le travail. Objectif : éviter qu'un état actif de la TX du Raspberry Pi
  bloque le démarrage du Pico.
- **Mode test avec Raspberry Pi 4** : USB PC débranché du Pico, Pico
  alimenté en autonome via VSYS, UART Raspberry Pi ↔ Pico rebranché
  complètement, tests via `/dev/ttyS0`.
- **Séquence pratique** : pour développer sur le Pico, débrancher la ligne
  Pi4 TX → Pico RX ; pour tester la communication avec le Raspberry Pi 4,
  rebrancher cette ligne, alimenter le Pico via VSYS, puis tester depuis le
  Raspberry Pi 4.

### Écart théorie/empirique des ticks par mètre (chenilles)

L'écart entre la valeur théorique de ticks par mètre (calculée à partir du
diamètre primitif des chenilles) et la valeur mesurée empiriquement sur le
robot réel est d'environ 11 %. Cet écart est attribuable au glissement des
chenilles plastique sur sol dur : il est inhérent au type de terrain et ne
représente pas une erreur de mesure.

Leçon : pour tout calcul d'odométrie, les valeurs mesurées empiriquement
sur le robot réel priment toujours sur les valeurs théoriques calculées à
partir de la géométrie. Les valeurs théoriques ne servent que de repère de
cohérence, jamais de valeur de calcul. Les valeurs actives sont dans
`robot_devastator_bringup/config/mecanique.yaml` ; la méthode et le
contexte de mesure sont documentés dans [parametres.md](parametres.md).

### Une calibration insuffisamment répétée fige du bruit en erreur systématique

Une calibration établie sur un nombre insuffisant de passes risque de figer
du bruit de mesure en erreur systématique plutôt que de corriger une
asymétrie réelle : le bruit d'une seule mesure (ou de trop peu de mesures)
se retrouve inscrit dans une constante de calibration, comme s'il s'agissait
d'un biais physique reproductible.

Leçon : avant d'inscrire une valeur de calibration dans la configuration,
vérifier qu'elle repose sur un signal reproductible sur plusieurs passes,
pas sur une mesure isolée. Voir `src/odometrie/README.md`, section
« Validation Phase 6 », pour l'exemple concret ayant fait émerger cette
leçon (calibration des ticks/mètre gauche/droite de l'odométrie).

### Bruit de démarrage (« clac ») de l'ampli I2S

L'ampli I2S (MAX98357 + PCM5102A) produit un clac audible au début de
chaque lecture séparée. Diagnostic : le bruit vient probablement de
l'ouverture et de la fermeture du flux audio par `aplay`, pas du routage
GPIO ni de `dtparam=audremap`.

Pistes essayées sans succès : `audremap`, lecture en flux continu,
tentative via SD/shutdown, pré-silence ou fade-in dans les WAV.

Décision : ne pas poursuivre ce chantier pour l'instant. L'audio reste une
capacité décorative de Devastator — purement informative, jamais requise
pour la sécurité ou le fonctionnement du robot. Pistes futures possibles si
le besoin redevient prioritaire : lecteur audio persistant ou solution matérielle anti-pop.

Contexte : Devastator, docs/decisions_et_lecons.md, section « Leçons apprises ».
Ajouter une nouvelle sous-section, suivant le format déjà en place (description,
conséquences observées, impact sur les phases futures si applicable) :

### Résolution du device audio ALSA « default » — instabilité entre redémarrages

Description : le device ALSA `default`, utilisé par `annonces_audio` (paramètre
`aplay -D default`), n'est pas garanti stable dans le temps : sa résolution dépend
de l'ordre d'énumération des cartes son au démarrage du noyau. Un changement dans
les périphériques USB présents au démarrage (notamment le branchement/débranchement
du RPLIDAR, lui-même une interface série USB) peut décaler cet ordre et faire
basculer `default` vers une autre carte (par exemple la sortie HDMI `vc4hdmi0`,
sans device réel à l'écoute), provoquant un échec de lecture
(`aplay: audio open error`) alors qu'aucun câblage ni code audio n'a changé.

Correction par index de carte — insuffisante, abandonnée : une première correction
avait fixé `default` sur l'index numérique de la carte HifiBerry
(`defaults.pcm.card 1`). Cette approche s'est révélée **elle-même instable** : le
même mécanisme d'énumération qui déplace `default` déplace aussi l'index attribué
à `sndrpihifiberry`, reproduisant le bris quelques jours plus tard sans changement
apparent.

Correction retenue — résolution par nom de carte : cibler la carte par son nom
stable (`sndrpihifiberry`, dérivé du pilote, indépendant de l'ordre d'énumération)
plutôt que par index, via `/etc/asound.conf` :

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

Le bloc `type plug` est nécessaire : un accès direct (`type hw`) sur le device par
nom a échoué avec `Channels count non available`, faute de conversion automatique
de format/canaux que `plug` fournit.

Impact sur les phases futures : ne plus utiliser d'index numérique de carte dans
aucune configuration ALSA sur ce Pi — toujours résoudre par nom (`cat /proc/asound/cards`
pour le confirmer). Revérifier `aplay -l` et `/etc/asound.conf` après tout ajout ou
retrait de périphérique USB, avant de conclure à un problème logiciel côté
`annonces_audio`.

### Un nœud validé manuellement en test peut rester absent du lancement de production sans le signaler

Description : `robot_state_publisher` a été lancé manuellement en test depuis la Phase 8
(package `robot_devastator_description`, fichiers `affichage.launch.py` /
`simulation.launch.py`) sans jamais être intégré à `devastator.launch.yaml`, le lancement
primaire de production. Rien dans le fonctionnement courant du robot ne signalait cet oubli :
aucun nœud de production ne dépendait de `/tf_static`, donc son absence passait inaperçue.

Conséquences observées : au démarrage normal du robot (`ros2 launch robot_devastator_bringup
devastator.launch.yaml`), `/tf_static` n'était jamais publié. Le problème n'est devenu visible
qu'en Phase 9, avec l'ajout du RPLIDAR A1M8 et du frame `laser_link` : RViz ne pouvait pas
résoudre les frames fixes du robot en usage normal, alors que la visualisation manuelle
(`simulation.launch.py` / `affichage.launch.py`) fonctionnait correctement puisqu'elle lance
`robot_state_publisher` elle-même.

Correction appliquée : ajout de `robot_state_publisher` à `devastator.launch.yaml`, en suivant
le patron YAML `$(command 'xacro ...')` pour charger `devastator.urdf.xacro` (voir
`robot_devastator_bringup/README.md`).

Impact sur les phases futures : un nœud fondamental (TF, description du robot, etc.) validé en
lancement de diagnostic ou manuel doit être ajouté à `devastator.launch.yaml` dès que son usage
devient permanent, même si aucun autre nœud de production n'en dépend encore. Une absence de ce
type ne se manifeste souvent qu'au moment où un sous-système qui en dépend réellement (ici
RViz/lidar) est ajouté, bien plus tard — vérifier explicitement la couverture du lancement de
production à chaque nouvelle intégration de capteur ou de frame TF.

### La typographie française « mot : mot » dans un xacro casse l'inférence de type YAML de launch_yaml

Description : charger un `robot_description` via `$(command 'xacro ...')` directement comme
`value:` d'un `param` dans un fichier `*.launch.yaml` échoue si le xacro généré contient, dans un
commentaire XML, la typographie française du deux-points (espace avant `:`), par exemple
`<!-- Matériaux : définis une seule fois... -->` dans `corps.xacro`. Le frontend `launch_yaml` fait
passer le résultat de la substitution par `yaml.safe_load()` pour déduire le type du paramètre ; ce
motif « mot espace deux-points espace mot » est alors interprété à tort comme une clé de mapping
YAML.

Conséquences observées : `ros2 launch` échoue au chargement du launch file avec l'erreur
`Failed to convert '<contenu XML>' using yaml rules: yaml.safe_load() failed — mapping values are
not allowed here`, pointant vers la ligne du commentaire français fautif dans le XML généré, pas
vers une erreur de syntaxe réelle du xacro.

Correction appliquée : sortir le nœud `robot_state_publisher` de `devastator.launch.yaml` vers un
fichier `robot_state_publisher.launch.py` dédié, qui traite le xacro en Python
(`xacro.process_file(...).toxml()`) et le passe directement dans le dictionnaire de paramètres du
`Node` — cela évite complètement l'inférence de type YAML, puisque Python n'a pas besoin de deviner
le type d'une valeur déjà typée `str`. Le fichier est inclus depuis `devastator.launch.yaml` via une
action `include`, ce qui préserve un point d'entrée de production unique. Voir
`robot_devastator_bringup/README.md`.

Impact sur les phases futures : tout futur `param` chargé dynamiquement via `$(command ...)` dans un
`*.launch.yaml` (ou `*.launch.xml`) est à risque si le contenu généré peut contenir du texte français
avec espace avant deux-points — commentaires XML, chaînes de configuration, messages générés,
etc. Si YAML ne suffit pas pour cette raison précise, isoler le nœud concerné dans un `*.launch.py`
minimal et l'inclure, plutôt que de reformuler la typographie des commentaires sources pour
contourner un détail d'implémentation de `launch_yaml`.

### Qualité du scan RPLIDAR A1M8 — zones mortes environnementales, pas capteur

Description : à fréquence stable (~6,8 Hz), le scan publié sur /scan présente des trous persistants même après cumul de plusieurs tours complets (RViz, Decay Time élevé). Test décisif : déplacer le robot dans la pièce et comparer les trous par rapport à l'angle du robot vs par rapport à la géométrie de la pièce.

Constat : la plupart des trous restent liés à des points fixes de la pièce (angles de mur rasants, surfaces peu réfléchissantes probablement), pas à un secteur angulaire fixe du robot. 

Conclusion : pas d'obstacle physique sur le châssis masquant le lidar — comportement normal d'un capteur bas de gamme (A1M8) en environnement réel, pas un défaut d'intégration.

Impact sur les phases futures : ne pas interpréter des trous de scan comme un problème de câblage ou de positionnement TF sans d'abord faire ce test de déplacement. Pertinent pour SLAM (Phase 10) : ces trous environnementaux persisteront, slam_toolbox devra les tolérer via la fusion multi-scans plutôt que de les traiter comme des erreurs de mesure.

### Démarrage automatique du RPLIDAR — comportement matériel non configurable

Description : le RPLIDAR A1M8 démarre en rotation et mesure dès qu'il reçoit son alimentation
(comportement documenté dans le datasheet Slamtec, section « System connection » : « After power
on each sub-system, RPLIDAR A1 start rotating and scanning »). Ce n'est pas un défaut du driver
`rplidar_ros` : le nœud `rplidar_composition` envoie même sa propre commande de démarrage à son
lancement (log observé : `rplidar_composition: Start`), donc le lidar tourne à la fois par défaut
matériel et par action explicite du driver.

Conséquences observées : le lidar tourne dès l'alimentation du robot, avant même le lancement de
ROS 2, et redémarre après un `Ctrl+C` puisque `rplidar_composition` cesse d'envoyer des commandes
mais le matériel retombe sur son comportement natif « alimenté = actif ». Aucun paramètre du
protocole RPLIDAR (datasheet, protocole d'interface) ne permet de changer cette valeur par défaut
à la source.

Correction retenue : ne jamais modifier le paquet externe `rplidar_ros` (comme `annonces_audio`
ne modifie jamais Piper). Un nœud pont dédié, `gestion_lidar`, encapsule le cycle de vie du lidar :
force la dormance (`/stop_motor`, qui coupe le moteur ET le laser, confirmé par l'absence totale
de publication sur `/scan` en dormance) au démarrage du programme, expose une interface simple
(`activer_lidar`/`desactiver_lidar`) pour toute source de commande (clavier aujourd'hui, mode
automatique ou Nav2 plus tard), et force à nouveau la dormance à son propre arrêt propre.

Impact sur les phases futures : ce patron (nœud pont dédié au cycle de vie d'un composant externe,
plutôt que de loger cette logique dans le premier nœud consommateur) est à réutiliser pour tout
futur composant à comportement matériel autonome — RealSense et ReSpeaker (Phases 11-12)
partagent potentiellement ce même risque de démarrage non supervisé.

Dette technique notée : le patron standard ROS 2 pour piloter le cycle de vie d'un nœud est l'interface `rclcpp_lifecycle` (nœuds à cycle de vie gérés, `configure`/`activate`/ `deactivate`), pas un nœud pont avec services custom. Le paquet `rplidar_ros` utilisé ici (officiel Slamtec, via apt) n'implémente pas cette interface — seulement des services propriétaires (`/stop_motor`, `/start_motor`). `gestion_lidar` est donc une solution pragmatique adaptée à ce paquet, pas le patron ROS 2 canonique. Si un driver RPLIDAR lifecycle-natif devient une alternative mûre, réévaluer si `gestion_lidar` peut être simplifié ou remplacé par des transitions lifecycle standards.

### Arrêt du RPLIDAR à la fermeture : le moteur repart à la fermeture du port série

Description : à `Ctrl+C` sur `devastator.launch.yaml`, le RPLIDAR s'arrête brièvement puis
repart, et reste en rotation après la fin complète du lancement.

Piste écartée #1 — course de signaux. `ros2 launch` envoie SIGINT à tous les nœuds à peu près en
parallèle, et `rplidar_composition` (C++) détruit ses services beaucoup plus vite que
`gestion_lidar` (Python/rclpy) ne remarque le signal. Premier log observé : l'appel final
`/stop_motor` échouait après le délai maximal complet, le service ayant déjà disparu. Une
correction par séquencement explicite (gestionnaire `OnShutdown` dans un `.launch.py` dédié,
appelant `/desactiver_lidar` de façon bloquante avant la propagation du SIGINT) a été essayée puis
**retirée** : complexité réelle (fichier de lancement supplémentaire, `ros2 service call` en
sous-processus dans un gestionnaire d'événement) sans bénéfice observé. Le simple fait de réduire
le délai de réveil du spin de `gestion_lidar` à 0.05 s suffit à gagner la course : log confirmé,
l'appel `/stop_motor` final aboutit en ~16 ms, avant la disparition du service.

Piste écartée #2 — commande de redémarrage du driver. Le log de fermeture ne montre **aucun**
`rplidar_composition: Start` après l'arrêt : le driver ne redémarre pas le moteur par une commande
ROS ni par son destructeur.

Cause retenue (matérielle), **confirmée par test** : sur le RPLIDAR A1, le moteur n'est pas
commandé par le protocole série mais par la ligne **DTR** de l'adaptateur USB-série CP2102
(`MOTOCTL`). Dans le SDK Slamtec, `stopMotor()` asserte DTR et `startMotor()` le relâche. Or Linux
abaisse DTR et RTS à la dernière fermeture du port : la simple sortie du processus
`rplidar_composition`, qui ferme le port série, relâche donc DTR et **remet le moteur en marche**.
Aucune commande ROS ne peut l'empêcher, puisque le phénomène se produit précisément quand le
driver n'existe plus.

Test de confirmation (robot arrêté, aucun processus ne tenant le port) : ouvrir le port en Python,
asserter DTR (`serial.Serial(PORT, 115200).dtr = True`), observer, puis désactiver `HUPCL` via
`termios` avant de fermer le port. Résultats obtenus sur le Raspberry Pi 4 :

1. DTR asserté → le moteur s'arrête immédiatement et reste arrêté **tant que le port est tenu
   ouvert**. La commande moteur passe donc bien par DTR, pas par le protocole série.
2. Port fermé, même avec `HUPCL` désactivé → le moteur **repart aussitôt**. Désactiver `HUPCL` ne
   suffit pas : le pilote `cp210x` désactive l'interface UART du CP2102 à la fermeture
   (`CP210X_IFC_ENABLE`/`UART_DISABLE`), ce qui réinitialise les lignes de contrôle quoi qu'en
   dise termios.

Piste écartée #3, donc : « asserter DTR puis fermer proprement le port » ne fonctionne pas sur ce
montage — testé, invalidé, ne pas y revenir. Le moteur ne peut rester arrêté que si un processus
**garde le port ouvert**.

Correction retenue : accepter la limite et **retirer** l'appel `/stop_motor` de fermeture de
`gestion_lidar`. Il n'apportait rien — la fermeture du port l'annule — et loguait « RPLIDAR arrêté
avant fermeture » alors que le moteur repartait juste après : un log faussement rassurant est pire
que pas de log du tout. Le RPLIDAR tourne donc entre deux sessions, jusqu'à la coupure
d'alimentation. Deux voies resteraient possibles si cela devenait gênant : un processus
« garde-port » qui survit au lancement en tenant le port avec DTR asserté (fonctionnerait, mais il
faudrait le tuer avant chaque relance puisqu'il occupe le périphérique — complexité jugée
disproportionnée ici), ou couper l'alimentation du RPLIDAR par relais commandé, seule solution
réellement propre.

Impact sur les phases futures : avant de soupçonner l'ordre des signaux ou le code d'un driver,
vérifier *quelle couche* commande réellement l'actionneur. Ici ce n'était ni ROS ni le protocole
série, mais une broche du convertisseur USB — et un état porté par une ligne de contrôle modem ne
survit pas à la fermeture du port, quoi qu'on règle dans termios. Corollaire général : un
actionneur dont l'état dépend d'un processus vivant ne peut pas être garanti après l'arrêt de ce
processus ; si la garantie compte, elle doit venir du matériel (relais, rail commutable). Pertinent
pour RealSense et ReSpeaker (Phases 11-12) seulement s'ils exposent un actionneur piloté hors
protocole.