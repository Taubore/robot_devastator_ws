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

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun odometrie robot_devastator_bringup
source install/setup.bash
ros2 launch robot_devastator_bringup odometrie.launch.yaml
```

Ce lancement isolé suppose qu'`interface_pico` tourne déjà (par exemple via
`interface_pico.launch.yaml`) pour que `/pico/encodeurs` soit publié. Depuis VSCode, utiliser la
tâche `ROS 2 - Lancer odométrie`.

## Test rapide

Lancer `interface_pico` puis `odometrie` dans deux terminaux séparés (ou les deux fichiers
`*.launch.yaml` correspondants), roues dans le vide pour un premier essai :

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

Validation du Phase 6 du `PLAN.md` (à faire sur le robot réel, roues au sol) :

- avancer d'environ 1 m en ligne droite → `pose.pose.position.x` (ou la norme `x`/`y` selon le cap
  de départ) entre `0.95` et `1.05` m ;
- tourner d'environ 90° sur place → le lacet extrait de `pose.pose.orientation` entre `1.47` et
  `1.67` rad ;
- effectuer un carré de 2 m de côté et mesurer l'écart entre la position finale estimée et le
  point de départ réel, pour documenter la dérive dans `PLAN.md`.

## Limites connues

- Aucune fusion de capteur : l'odométrie repose uniquement sur les encodeurs, sans IMU ni
  correction visuelle.
- La dérive angulaire et linéaire n'est pas corrigée ; elle s'accumule avec la distance parcourue
  et les glissements des chenilles.
- Le nœud ne détecte pas un appel à `/pico/reset_encodeurs` pendant son fonctionnement : les
  compteurs de ticks repartent de zéro côté Pico, mais `odometrie` continue de calculer un delta
  par rapport aux anciens ticks mémorisés, ce qui produit un saut de pose au message suivant.
  Redémarrer `odometrie` après un `/pico/reset_encodeurs` pour repartir sur une référence de
  ticks propre (`/odometrie/reset` seul ne suffit pas : il remet `x`, `y`, `theta` à zéro mais ne
  resynchronise pas la référence interne de ticks).
