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
