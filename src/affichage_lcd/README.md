# affichage_lcd

Nœud ROS 2 d'affichage sur l'écran LCD Waveshare 2 pouces (ST7789V). Troisième et
dernière couche de l'empilement d'affichage, au-dessus du pilote bas niveau et du
rendu texte fournis par [`lcd_st7789v`](../lcd_st7789v/README.md) : `EcranSt7789v` et
`GrilleTexte`. Ce nœud ne fait aucun accès matériel direct.

## Rôle

Traduit l'état courant du robot en deux pages affichées à l'écran :

- **Page bouche** (page 0) : visage simple dessiné avec Pillow, imposée pendant une
  annonce vocale (`/robot/parole_en_cours`), et forcée juste après un passage du mode
  manuel vers le mode autonomie.
- **Page tableau de bord** (page 1) : mode de conduite, tension/courant des deux rails
  d'alimentation, consignes moteur gauche/droite réellement appliquées.

Les abonnements ne font que mettre à jour un état interne en mémoire ; un timer à
10 Hz est le seul endroit du nœud qui dessine à l'écran.

### Mise en page de la page tableau de bord

```
MODE : MANUEL
--------------------------------
Logique  : 12.3 V   0.4 A
Moteur   : 11.8 V   1.2 A
--------------------------------
Gauche   : avance   650
Droite   : avance   650
```

Une couleur par bloc (mode, alimentation, consignes moteur), rouge exclu (réservé aux
erreurs). Le courant est toujours affiché en valeur absolue : seule la tension sert de
repère de charge, voir `docs/parametres.md`. Un champ affiche `--` si la mesure
correspondante dépasse `peremption_alimentation_s` sans nouvelle réception.

## Paramètres ROS 2

| Paramètre | Défaut | Rôle |
|---|---|---|
| `peremption_alimentation_s` | `3.0` | Au-delà de ce délai sans réception d'un `BatteryState` pour un rail, ce rail affiche `--` plutôt que sa dernière valeur connue. |
| `periode_rafraichissement_s` | `0.1` | Période du timer d'affichage (10 Hz par défaut). |
| `retroeclairage_pourcent` | `80.0` | Intensité du rétroéclairage réglée au démarrage (0 à 100). |

## Topics consommés

| Topic | Type | Rôle |
|---|---|---|
| `/robot/mode_conduite` | `std_msgs/msg/String` | `manuel` ou `autonomie` ; un front manuel→autonomie force la page bouche. |
| `/robot/parole_en_cours` | `std_msgs/msg/Bool` | Impose la page bouche tant que vrai. Abonnement en QoS *transient local*, profondeur 1, pour connaître l'état même si ce nœud démarre après la dernière publication. |
| `/affichage/page_suivante` | `std_msgs/msg/Empty` | Bascule vers la page suivante (bouclage), ignoré pendant une annonce vocale. |
| `/alimentation/logique`, `/alimentation/moteur` | `sensor_msgs/msg/BatteryState` | Tension et courant des rails logique et moteur. |
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | Consigne gauche/droite réellement appliquée, après arbitrage. |

Aucun topic publié, aucun service, aucune action.

## Exemple de lancement

Isolé, sans autre nœud (tous les signaux ci-dessus peuvent être publiés à la main) :

```bash
ros2 run affichage_lcd affichage_lcd
```

L'intégration à `devastator.launch.yaml` est une étape séparée, hors de portée de ce
package pour l'instant.

## Test simple

Avec le nœud seul lancé sur le Raspberry Pi 4 :

```bash
# Page 1 affichée au démarrage, avec "--" partout sur les champs d'alimentation
ros2 topic pub --once /alimentation/logique sensor_msgs/msg/BatteryState \
  '{voltage: 7.2, current: -0.43}'
# La tension/courant apparaissent sur la ligne "Log"

ros2 topic pub --once /robot/mode_conduite std_msgs/msg/String '{data: manuel}'
ros2 topic pub --once /robot/mode_conduite std_msgs/msg/String '{data: autonomie}'
# Bascule manuel -> autonomie : force la page bouche

ros2 topic pub --once /affichage/page_suivante std_msgs/msg/Empty '{}'
# Retour à la page 1 ("p")

ros2 topic pub --once /robot/mode_conduite std_msgs/msg/String '{data: autonomie}'
# Republication de "autonomie" sans changement : ne force rien, page 1 reste affichée

ros2 topic pub /robot/parole_en_cours std_msgs/msg/Bool '{data: true}' \
  --qos-durability transient_local --once
# Page bouche imposée

ros2 topic pub --once /affichage/page_suivante std_msgs/msg/Empty '{}'
# Ignoré : la page reste sur la bouche tant que /robot/parole_en_cours est vrai
```

## Limites connues

- Une seule page de statut pour l'instant (page 1) ; le bouclage de
  `/affichage/page_suivante` n'alterne donc qu'entre les pages 0 et 1.
- La bouche de la page 0 est une forme simple statique, non animée.
