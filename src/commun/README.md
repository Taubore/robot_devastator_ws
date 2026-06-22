# commun

`commun` est le package ROS 2 qui regroupe les interfaces partagées entre tous les packages du
projet Devastator. Il existe séparément pour éviter les dépendances circulaires : tout package qui
produit ou consomme un message de ce projet importe uniquement `commun`, sans dépendre du package
qui l'utilise.

## Messages définis

### `commun/msg/ConsigneMoteurs`

| Champ | Type | Rôle |
|---|---|---|
| `gauche` | `int16` | Consigne du moteur gauche |
| `droite` | `int16` | Consigne du moteur droit |

Plage de valeurs : `-1000` à `1000`. La valeur `0` correspond à l'arrêt. Les valeurs positives
font avancer le moteur, les valeurs négatives le font reculer. Ne pas corriger un mauvais sens
de rotation en logiciel ; corriger le câblage au MDD3A.

### `commun/msg/EtatEncodeurs`

| Champ | Type | Rôle |
|---|---|---|
| `gauche_ticks` | `int32` | Ticks accumulés par l'encodeur du moteur gauche |
| `droite_ticks` | `int32` | Ticks accumulés par l'encodeur du moteur droit |

Les ticks augmentent en marche avant et diminuent en marche arrière. Le reset s'effectue via le
service `/pico/reset_encodeurs`.

## Nœuds exécutables

Ce package ne contient aucun nœud exécutable. Il ne produit que des types de messages.

## Build

Ce package utilise `ament_cmake` avec `rosidl_default_generators` pour générer les types de
messages. Toute modification d'un fichier `.msg` nécessite un rebuild complet du package et de
tous les packages qui en dépendent.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun
source install/setup.bash
```

En cas d'artefacts obsolètes après un renommage ou une suppression de `.msg`, utiliser le
nettoyage ciblé depuis VSCode : `Tasks: Run Task > ROS 2 - Nettoyer packages Devastator`.
