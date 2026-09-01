# odometrie

`odometrie` est le package ROS 2 qui calcule la position estimée du robot (odométrie) à partir
des ticks encodeurs publiés par `interface_pico`, sans GPS ni caméra.

## Rôle du fichier principal

- `odometrie/odometrie.py` : nœud ROS 2 `odometrie`. S'abonne à `/pico/encodeurs`, convertit le
  delta de ticks depuis le message précédent en distance parcourue par chaque chenille, applique
  la cinématique différentielle classique pour cumuler `x`, `y`, `theta`, puis publie `/odom` et
  la transform `odom → base_footprint`.

## Interfaces ROS 2

- Topic d'entrée `/pico/encodeurs` : `commun/msg/EtatEncodeurs`, ticks gauche et droit cumulés
- Topic publié `/odom` : `nav_msgs/msg/Odometry`, publié à chaque message reçu sur
  `/pico/encodeurs` (donc à la fréquence de ce topic, ~10 Hz), pas de timer séparé
- Transform publiée `odom → base_footprint` : via `tf2_ros`, même fréquence que `/odom`
- Service `/odometrie/reset` : `std_srvs/srv/Trigger`, remet `x`, `y`, `theta` à zéro sans toucher
  aux compteurs de ticks du Pico (indépendant de `/pico/reset_encodeurs`)

## Cinématique appliquée

À chaque message, le delta de ticks gauche et droit depuis le message précédent est converti en
distance via `ticks_par_metre_gauche` et `ticks_par_metre_droite`. La distance moyenne parcourue
et la rotation `delta_theta` (différence des distances gauche/droite divisée par `entraxe_m`)
sont ensuite intégrées par arc médian : le déplacement est appliqué selon le cap moyen tenu
pendant le cycle (`theta + delta_theta / 2`) plutôt que selon le cap de départ, ce qui reste
fidèle à la trajectoire même lors d'une rotation notable entre deux messages. Le premier message
reçu après le démarrage (ou après un redémarrage) sert uniquement de référence ; aucun delta n'est
intégré avant le second message.

Comme documenté en Phase 6 du `PLAN.md`, cette estimation dérive avec le temps (comme marcher les
yeux fermés). La dérive est attendue et documentée, pas corrigée par ce nœud.

## Paramètres

- `ticks_par_tour` : ticks encodeur par tour de roue, mesuré empiriquement
- `ticks_par_metre_gauche` : ticks par mètre parcouru côté gauche
- `ticks_par_metre_droite` : ticks par mètre parcouru côté droit
- `ticks_par_metre_moyen` : ticks par mètre parcouru, moyenne des deux côtés (référence, non
  utilisé directement par le calcul)
- `entraxe_m` : entraxe effectif entre les deux chenilles, en mètres

Ces valeurs sont mesurées en Phase 3 et consignées dans `docs/parametres.md`. Le lancement
Devastator charge directement `robot_devastator_bringup/config/mecanique.yaml`, qui contient déjà
une clé racine `odometrie:` correspondant exactement à ces paramètres — aucun fichier de
configuration dédié n'a été dupliqué pour ce nœud.

## Lancement dans Devastator

`odometrie` est démarré par le lancement primaire `devastator.launch.yaml`, avec le fichier de
paramètres `robot_devastator_bringup/config/mecanique.yaml`. Aucun lancement dédié : le nœud est
du calcul pur sur `/pico/encodeurs` et ne capture pas le terminal.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico odometrie robot_devastator robot_devastator_bringup
source install/setup.bash
ros2 launch robot_devastator_bringup devastator.launch.yaml
```

Pour un diagnostic de l'odométrie seule, lancer `diag_interface_pico.launch.yaml` puis, dans un
autre terminal sourcé :

```bash
ros2 run odometrie odometrie --ros-args --params-file src/robot_devastator_bringup/config/mecanique.yaml
```

## Test rapide

Roues dans le vide pour un premier essai, `/odom` et la TF observés pendant que le robot est
poussé à la main :

```bash
ros2 topic echo /odom
ros2 topic echo /tf
```

Pousser ou faire rouler le robot à la main et observer que `pose.pose.position.x/y` et
`pose.pose.orientation` évoluent de façon cohérente avec le déplacement réel. Remettre la pose à
zéro sans toucher aux ticks du Pico :

```bash
ros2 service call /odometrie/reset std_srvs/srv/Trigger
```

## Validation Phase 6 (2026-08-23, sol dur, chenilles plastique)

Mesures effectuées sur le robot réel, roues au sol, ruban à mesurer.

| Essai | Résultat | Critère | Verdict |
|---|---|---|---|
| Avance 1 m, 3 passes | sous-estimation de 1,0 à 1,6 % | 0,95–1,05 m | atteint |
| Rotation 90°, 3 passes | 1,568 / 1,490 / 1,574 rad | 1,47–1,67 rad | atteint |
| Tour complet, lent | 6,36 rad (attendu 6,28) | — | écart 1 % |
| Tour complet, rapide | 6,28 rad | — | écart nul |
| Carré 1,5 m, avant correction | `/odom` 1,16 m, réel 0,04 m | documenter | dérive 1,12 m |
| Carré 1,5 m, après correction | `/odom` 0,94 m, réel 0,09 m | documenter | dérive 0,85 m |

### Correction de calibration appliquée

Les facteurs `ticks_par_metre_gauche` (10 492) et `ticks_par_metre_droite` (10 373) mesurés en
Phase 3 différaient de 1,14 %. Cet écart ne corrigeait pas une asymétrie réelle des chenilles : il
en introduisait une. Le nœud déduisant le cap de la différence entre les deux côtés, une ligne
droite de 1,5 m produisait un cap fantôme de 0,10 rad (5,7°) alors que le robot ne tournait pas.

Après égalisation des deux facteurs à 10 432, la même ligne droite donne 0,016 rad (0,9°).

Leçon retenue : une calibration établie sur un nombre insuffisant de passes fige du bruit de
mesure en erreur systématique. Vérifier qu'une correction repose sur un signal reproductible
avant de l'inscrire dans la configuration.

## Limites connues

- Aucune fusion de capteur : l'odométrie repose uniquement sur les encodeurs, sans IMU ni
  correction visuelle.
- La dérive angulaire et linéaire n'est pas corrigée ; elle s'accumule avec la distance parcourue
  et les glissements des chenilles.
- **Cause résiduelle non identifiée.** Après correction de la calibration, il subsiste 0,85 m de
  dérive sur un carré de 1,5 m. Signature relevée : la composante `y` finale est restée identique
  au millimètre près entre les deux essais (−0,361 m avant et après), alors que la composante `x`
  a diminué. Deux mécanismes indépendants sont donc en cause ; seul celui agissant sur l'axe de
  départ a été corrigé. L'`entraxe_m` de 0,197 m, mesuré au ruban et jamais validé
  expérimentalement, est le suspect principal — l'entraxe effectif d'un chenillé dépasse
  généralement l'écartement géométrique. Hypothèse non confirmée : le test du tour complet ne
  révèle aucune erreur de rotation.
- Le nœud ne détecte pas un appel à `/pico/reset_encodeurs` pendant son fonctionnement : les
  compteurs de ticks repartent de zéro côté Pico, mais `odometrie` continue de calculer un delta
  par rapport aux anciens ticks mémorisés, ce qui produit un saut de pose au message suivant.
  Redémarrer `odometrie` après un `/pico/reset_encodeurs` pour repartir sur une référence de
  ticks propre (`/odometrie/reset` seul ne suffit pas : il remet `x`, `y`, `theta` à zéro mais ne
  resynchronise pas la référence interne de ticks).