
# Contrôle moteurs — Pico WH + MDD3A

## Configuration ROS 2 de l'interface Pico

Le nœud `interface_pico` utilise la liaison UART vers le Pico WH. Les paramètres ajustables
(port, débit, timeouts, périodes de sondage) vivent dans
`src/robot_devastator_bringup/config/interface_pico.yaml` — s'y référer pour les valeurs actives.

Le comportement d'autonomie simple est configuré dans
`src/robot_devastator_bringup/config/autonomie_simple.yaml` (vitesses, angles de tourelle,
distances de déclenchement, `actif_au_demarrage`).

La téléopération clavier est configurée dans
`src/robot_devastator_bringup/config/teleop_clavier.yaml` (vitesses et pas d'incrément).

L'arbitre de commandes moteur est configuré dans
`src/robot_devastator_bringup/config/arbitre_commande_moteurs.yaml` (mode initial, période de
publication, délai d'expiration).

Association d'angles de tourelle validée sur le robot (valeurs actives dans
`autonomie_simple.yaml`) : l'angle le plus faible oriente la tourelle vers la gauche, le plus
élevé vers la droite.

L'affectation GPIO des moteurs et le câblage UART Raspberry Pi 4 ↔ Pico WH sont documentés dans
[docs/connexions.md](connexions.md), seule source pour le câblage. Le piège de démarrage du Pico
lié à l'état de la TX du Raspberry Pi est documenté dans
[docs/decisions_et_lecons.md](decisions_et_lecons.md).

## Convention logique (figée)

- avancer :
  - PWM sur entrée A
  - entrée B = 0

- reculer :
  - entrée A = 0
  - PWM sur entrée B

- arrêter :
  - A = 0
  - B = 0

Le câblage des moteurs au MDD3A (couleurs, correspondance entrée A/B) est documenté dans
[docs/connexions.md](connexions.md). La décision de corriger le sens du moteur gauche au câblage
plutôt qu'en logiciel est documentée dans
[docs/decisions_et_lecons.md](decisions_et_lecons.md).

## Fréquence PWM

- Valeur actuelle : 1000 Hz, fixée côté firmware Pico (aucun paramètre ROS 2 associé)
- Ajustable ultérieurement selon bruit / rendement

## Protocole UART

Le format de commande (texte ASCII terminé par fin de ligne) et la plage de consigne moteur sont
des invariants du contrat d'interface :

### Convention de consigne

- plage : `-1000` à `1000`
- signe :
  - positif = avancer
  - négatif = reculer
- valeur absolue = intensité PWM
- `0` = arrêt

Le détail des commandes UART, des services ROS 2 et de la sécurité (arrêts automatiques,
timeouts) est documenté dans [docs/contrat_pico_ros2.md](contrat_pico_ros2.md), seule source pour
le protocole Pico.

## Paramètres mécaniques

Méthode et contexte de calibration : mesures réalisées en Phase 3 (2026-06-24) sur sol dur, par
déplacement en ligne droite sur 1 m et comptage des ticks encodeurs. Ces mesures physiques et
intermédiaires sont conservées ici à titre de référence et d'historique de calibration ; les
valeurs actives utilisées par le nœud `odometrie` (ticks par tour, ticks par mètre moyen, entraxe)
vivent dans `robot_devastator_bringup/config/mecanique.yaml`, déjà chargé par le lancement
principal — ne pas les recopier ici.

| Paramètre            | Valeur    | Unité      | Note                                    |
|----------------------|-----------|------------|-----------------------------------------|
| Nombre de dents      | 13        | —          | Pignon d'entraînement                   |
| Pas chenille         | 9,5       | mm         | Centre à centre d'un maillon            |
| Diamètre extérieur (pointe à pointe) | 42,90 | mm | Mesuré au pied à coulisse, 2026-09-01 |
| Diamètre primitif    | 39,32     | mm         | Calculé : N × p / π                    |
| Ticks/m théorique    | 11 715    | ticks/m    | Calculé à partir du diamètre primitif   |
| Ticks/m gauche       | 10 492    | ticks/m    | Mesuré empiriquement sur 1 m, mais remplacé par la valeur moyenne le 2026-08-23 car l'étalonnage ne semble pas adéquat |
| Ticks/m droite       | 10 373    | ticks/m    | Mesuré empiriquement sur 1 m, mais remplacé par la valeur moyenne le 2026-08-23 car l'étalonnage ne semble pas adéquat |

L'écart entre la valeur théorique et la valeur empirique moyenne, et la raison de privilégier les
valeurs empiriques pour l'odométrie, sont documentés dans
[docs/decisions_et_lecons.md](decisions_et_lecons.md).

# Affichage LCD — ST7789V

- Fréquence SPI retenue : 32 MHz. 

# Surveillance de l'alimentation — INA260

Nœud `surveillance_alimentation`, paramètres ajustables (bus I2C, cadence, moyennage, adresses,
signe du courant, seuils, hystérésis, temporisation, rappels) dans
`robot_devastator_bringup/config/surveillance_alimentation.yaml` — s'y référer pour les valeurs
actives. Le package est réutilisable : aucune valeur propre à Devastator n'est codée en Python.
Le câblage I2C et les adresses physiques des deux capteurs sont documentés dans
[docs/connexions.md](connexions.md).

## Conversion INA260 (datasheet TI SBOS656C)

Invariants du capteur, indépendants de toute configuration ROS 2 :

- Registres : `0x00` config, `0x01` courant, `0x02` tension bus, `0xFE`/`0xFF` identification
- LSB courant : 1,25 mA/bit, valeur en complément à deux sur 16 bits
- LSB tension bus : 1,25 mV/bit, toujours positive
- Mots 16 bits transmis octet de poids fort en premier

## Signe du courant

`sensor_msgs/msg/BatteryState` veut un `current` négatif en décharge. Le câblage VIN+/VIN- des
deux INA260 de Devastator donne des lectures positives alors que les deux rails sont en décharge
permanente. Le paramètre `rail.<nom>.signe_courant` (`1` ou `-1`, rejeté au démarrage sinon)
multiplie la lecture avant publication ; il est propre à chaque rail, car rien ne garantit que
deux capteurs soient câblés dans le même sens sur un autre robot. Valeur active des deux rails :
voir `surveillance_alimentation.yaml`.

## Seuils d'alerte

Les seuils sont exprimés en volts absolus, jamais dérivés du nombre de cellules en code. Valeurs
actives par rail : voir `surveillance_alimentation.yaml`.

- **Porte de courant** : un seuil n'est évalué que si `abs(courant)` est sous la valeur configurée ;
  sous charge la tension chute par la résistance interne et ne renseigne pas l'état de charge.
- **Temporisation** : la condition doit être maintenue le délai configuré avant l'émission de
  l'événement. Le délai est suivi par un accumulateur de durée. Porte de courant fermée = condition
  *inconnue* : l'accumulateur est laissé intact sans rien accumuler, donc une conduite qui
  alterne accélérations et courts arrêts ne remet jamais la temporisation à zéro. Il ne repart
  de zéro que sur une mesure valide au-dessus du seuil.
- **Hystérésis** : un seuil armé ne se désarme que si la tension repasse au-dessus de
  `seuil + hystérésis`, à courant faible.
- **Rappel périodique** : tant qu'un seuil reste armé, l'événement est réémis toutes les
  `rail.<nom>.periode_rappel_<niveau>_s` secondes (`0` = émission unique). Le rappel suit
  l'armement (il continue porte fermée) et son compteur se réinitialise au désarmement.

## Événements publiés sur `/robot/evenement`

`batterie_logique_faible`, `batterie_logique_critique`, `batterie_moteur_faible`,
`batterie_moteur_critique`. Libellés définis dans le YAML et repris dans `EVENEMENTS_ANNONCES`
d'`annonces_audio`, qui les prononce. Aucune variante silencieuse sur ces quatre événements : une
alerte batterie est toujours annoncée. Le nœud tourne en permanence via `devastator.launch.yaml`.

## Repères de mesure et consommation

Les repères de consommation (courant par rail et par état du robot, tensions typiques au repos,
courant du rail moteur sous charge, veille hors séance) sont regroupés dans la section
**« Consommation du robot »** du [README.md](../README.md).

Rappel utile pour le réglage des seuils : la surveillance de batterie se fait sur la **tension**,
jamais sur le courant. Le courant sert seulement à fermer la porte de courant quand le robot
consomme.

## Protection — fusible du rail moteur

Un **fusible rapide 10 A, format 20 mm**, est monté sur le fil positif du rail moteur, en amont
du MDD3A et en série avec l'INA260 `0x41`. Il protège le câblage moteur contre un courant de
blocage de chenilles prolongé, qui a déjà provoqué un échauffement du câblage de masse.
