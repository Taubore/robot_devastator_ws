# surveillance_alimentation

`surveillance_alimentation` est le package ROS 2 qui surveille la tension et le courant des
batteries d'un robot mobile à partir de capteurs **Adafruit INA260** sur bus I2C. Il publie un
`sensor_msgs/msg/BatteryState` par rail d'alimentation et émet un événement quand une tension
reste trop basse assez longtemps.

Le package est volontairement indépendant de Devastator : aucune dépendance à `commun` ni à
quoi que ce soit de spécifique au robot. Toute valeur propre à une installation (bus I2C,
adresses, seuils en volts, libellés d'événement, technologie de batterie) vit dans le YAML. Il
peut être récupéré tel quel sur un autre robot en ne changeant que le fichier de paramètres.

## Dépendance système

Le pilote utilise `smbus2` (accès I2C brut), pas la bibliothèque Adafruit/Blinka. Sur le
Raspberry Pi 4 :

```bash
sudo apt install python3-smbus2
```

L'utilisateur qui lance le nœud doit appartenir au groupe `i2c` (`sudo usermod -aG i2c $USER`,
puis rouvrir la session) et le bus I2C doit être activé (`dtparam=i2c_arm=on`).

## Rôle des fichiers principaux

- `surveillance_alimentation/ina260.py` : pilote pur du circuit INA260 (`LecteurINA260`).
  Ne connaît que le protocole : il reçoit un `SMBus` déjà ouvert, lit la tension bus et le
  courant, vérifie l'identité du circuit et programme le moyennage matériel. Registres et
  facteurs de conversion vérifiés contre le datasheet TI **SBOS656C** (voir l'en-tête du
  fichier pour les références de section). Réutilisable hors ROS 2.
- `surveillance_alimentation/surveillance_alimentation.py` : nœud ROS 2
  `surveillance_alimentation`. Ouvre un bus I2C partagé, instancie un `LecteurINA260` par rail,
  publie les `BatteryState` à cadence fixe et applique la logique d'alerte.

## Interfaces ROS 2

- Topics publiés, un par rail (nom configurable) : `sensor_msgs/msg/BatteryState`, à
  `periode_publication_s` (défaut 1 Hz). Champs remplis : `voltage`, `current`,
  `power_supply_technology`, `power_supply_status` (`DISCHARGING` en marche normale, `UNKNOWN`
  si le capteur est illisible), `present`. `percentage` et les champs de capacité sont laissés
  à `NaN` (voir *Choix de conception*).
- Topic d'événement (défaut `/robot/evenement`) : `std_msgs/msg/String`. Le nœud y publie le
  libellé configuré quand un seuil est armé. Les libellés sont des paramètres YAML, pas des
  constantes. Sur Devastator, ce topic est consommé par `annonces_audio`.

Aucun service ni action.

## Logique d'alerte

La tension d'un accu chute sous charge par la résistance interne
(`V = Vfem - R_interne x I`). Une lecture de tension n'indique l'état de charge que si le
courant est faible. Trois garde-fous, tous configurables par rail :

1. **Porte de courant** : un seuil n'est évalué que si `abs(courant) < courant_max_evaluation_a`.
2. **Temporisation** : la condition (tension sous le seuil, à courant faible) doit être
   maintenue `temporisation_s` secondes avant que l'événement soit émis. La durée est suivie
   par un accumulateur, pas par un horodatage : une condition de surveillance a trois états —
   vraie, fausse, inconnue. **Porte de courant fermée = inconnue**, pas fausse : l'accumulateur
   est alors laissé intact sans rien y ajouter, pour qu'une conduite alternant accélérations et
   courts arrêts ne remette jamais la temporisation à zéro. Tension au-dessus du seuil à courant
   faible = fausse : l'accumulateur repart de zéro.
3. **Hystérésis** : un seuil armé ne se désarme que lorsque la tension repasse au-dessus de
   `seuil + hysteresis_rearmement_v`, et seulement à courant faible.
4. **Rappel périodique** : une alerte batterie est un état persistant. Tant qu'un seuil reste
   armé, l'événement est réémis toutes les `periode_rappel_<niveau>_s` secondes (`0` = émission
   unique). Le rappel suit l'état d'armement et non la mesure : il continue même pendant que la
   porte de courant est fermée, et son compteur se réinitialise au désarmement. L'avertissement
   et le critique se rappellent chacun à leur rythme, sans hiérarchisation : les deux libellés
   sont publiés si les deux seuils sont armés (la déduplication appartient au consommateur).

Deux niveaux par rail : `avertissement` et `critique`, chacun avec son seuil en volts absolus
et son libellé d'événement. Un seuil dont la tension est `0` est désactivé.

Le signe du courant lu est ramené au contrat `BatteryState` (négatif en décharge) par le
paramètre `signe_courant` propre à chaque rail (`1` ou `-1`, selon le câblage VIN+/VIN- du
capteur). La logique d'alerte travaille sur `abs(courant)` et n'est pas affectée par ce choix.

## Paramètres

### Globaux

| Paramètre | Défaut | Rôle |
|---|---|---|
| `bus_i2c` | `1` | Numéro du bus I2C (`/dev/i2c-<n>`) |
| `periode_publication_s` | `1.0` | Cadence de publication et d'évaluation |
| `nb_echantillons_moyenne` | `64` | Moyennage matériel INA260 (1/4/16/64/128/256/512/1024) |
| `echecs_avant_erreur` | `5` | Échecs I2C consécutifs avant de passer du WARN à l'ERROR |
| `topic_evenement` | `/robot/evenement` | Topic `String` des événements d'alerte |
| `rails` | `['logique', 'moteur']` | Noms des rails surveillés |

### Par rail (`rail.<nom>.*`)

| Paramètre | Rôle |
|---|---|
| `adresse_i2c` | Adresse I2C du INA260 (entier ; `64` = `0x40`) |
| `topic` | Topic `BatteryState` du rail |
| `frame_id` | `header.frame_id` du message |
| `technologie` | `nimh`, `lion`, `lipo`, `life`, `nicd`, `limn` ou `inconnue` |
| `signe_courant` | Facteur appliqué au courant lu avant publication : `1` ou `-1` (rejeté sinon). `-1` si le câblage VIN+/VIN- du capteur donne un courant positif en décharge |
| `seuil_avertissement_v` | Seuil bas d'avertissement, en volts absolus (`0` = désactivé) |
| `seuil_critique_v` | Seuil bas critique, en volts absolus (`0` = désactivé) |
| `hysteresis_rearmement_v` | Marge de tension au-dessus du seuil pour désarmer |
| `courant_max_evaluation_a` | Courant absolu maximal pour juger la tension |
| `temporisation_s` | Durée de maintien de la condition avant d'alerter |
| `periode_rappel_avertissement_s` | Période de réémission de l'événement tant que l'avertissement est armé (`0` = émission unique) |
| `periode_rappel_critique_s` | Période de réémission de l'événement tant que le critique est armé (`0` = émission unique) |
| `evenement_avertissement` | Libellé publié sur `topic_evenement` (`''` = désactivé) |
| `evenement_critique` | Libellé publié sur `topic_evenement` (`''` = désactivé) |

Sur Devastator, ces valeurs sont dans
`robot_devastator_bringup/config/surveillance_alimentation.yaml`.

## Choix de conception

- **`percentage` à `NaN`.** La courbe de décharge d'un accu NiMH est trop plate (~1,2 V/cellule
  sur l'essentiel de la capacité) pour convertir une tension en pourcentage de charge honnête.
  Publier une estimation serait trompeur ; la surveillance se fait sur des seuils de tension.
- **Seuils en volts absolus.** Ils ne sont jamais calculés à partir d'un nombre de cellules
  dans le code : le YAML porte la valeur finale, ce qui rend le module valable pour n'importe
  quelle chimie et n'importe quel nombre de cellules.
- **Robustesse.** Une erreur de lecture I2C ne tue jamais le nœud : les échecs consécutifs sont
  comptés, un `BatteryState` en `POWER_SUPPLY_STATUS_UNKNOWN` continue d'être publié, et l'autre
  rail n'est pas affecté. Un capteur absent au démarrage ne bloque pas le lancement.

## Journalisation

Silence en fonctionnement normal, aucun log périodique de mesure. `WARN` sur franchissement de
seuil (dans les deux sens) et sur erreur I2C transitoire. `ERROR` unique quand un capteur
devient illisible durablement, puis silence jusqu'au rétablissement.

## Lancement

Ce package n'est pas encore intégré à `devastator.launch.yaml` : mise au point isolée d'abord.

```bash
ros2 launch robot_devastator_bringup diag_surveillance_alimentation.launch.yaml
```

## Procédure de test CLI sur le Raspberry Pi 4

Terminal SSH sourcé. Les capteurs ne sont alimentés (rail logique 3,3 V) que robot allumé.

```bash
# 1. Dépendance système
sudo apt install python3-smbus2
```

```bash
# 2. Détection I2C : les deux INA260 doivent apparaître
i2cdetect -y 1
```

Sortie attendue : `40` et `41` visibles dans la grille.

```bash
# 3. Build
cd ~/projets/robot_devastator_ws
colcon build --symlink-install --packages-select surveillance_alimentation robot_devastator_bringup
source install/setup.bash
```

```bash
# 4. Lancement du nœud seul
ros2 launch robot_devastator_bringup diag_surveillance_alimentation.launch.yaml
```

```bash
# 5. Dans un second terminal sourcé : observer les mesures
ros2 topic echo /alimentation/logique
```

```bash
ros2 topic echo /alimentation/moteur
```

```bash
# 6. Vérifier la cadence (~1 Hz)
ros2 topic hz /alimentation/logique
```

```bash
# 7. Comparer voltage publié et voltmètre physique du robot
#    (VOLTM_LOGIQUE et VOLTM_MOTEUR). Écart attendu : quelques dizaines de mV.
```

```bash
# 8. Vérifier le signe du courant : robot au repos, les deux topics doivent
#    publier un current négatif (décharge). Champ current de :
ros2 topic echo /alimentation/logique --field current
```

```bash
ros2 topic echo /alimentation/moteur --field current
```

```bash
# 9. Écouter les événements d'alerte
ros2 topic echo /robot/evenement
```

```bash
# 10. Test de seuil + rappel : relever temporairement seuil_avertissement_v du
#     rail logique au-dessus de la tension réelle dans surveillance_alimentation.yaml,
#     rebuild, relancer. Après temporisation_s, un String "batterie_logique_faible"
#     est publié. Il doit ensuite être réémis toutes les
#     periode_rappel_avertissement_s (abaisser cette valeur, p. ex. 15.0, le temps
#     du test). Remettre les valeurs d'origine ensuite.
```

```bash
# 11. Non-rappel après désarmement : seuil de test toujours relevé, remettre
#     seuil_avertissement_v sous la tension réelle (ou remonter la tension), rebuild,
#     relancer. Après le WARN "seuil avertissement rétabli", plus aucun String ne
#     doit sortir sur /robot/evenement.
```

## Limites connues

- Le nœud publie `power_supply_status = DISCHARGING` dès qu'une lecture réussit : il ne détecte
  pas une charge (le robot ne se recharge pas en fonctionnement).
- Pas d'estimation d'autonomie restante : hors périmètre pour une chimie NiMH.
- Les capteurs sont sur le rail logique 3,3 V : aucune lecture n'est possible robot éteint.
