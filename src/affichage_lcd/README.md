# affichage_lcd

Nœud ROS 2 d'affichage sur l'écran LCD Waveshare 2 pouces (ST7789V). Troisième et
dernière couche de l'empilement d'affichage, au-dessus du pilote bas niveau et du
rendu texte fournis par [`lcd_st7789v`](../lcd_st7789v/README.md) : `EcranSt7789v` et
`GrilleTexte`. Ce nœud ne fait aucun accès matériel direct.

## Rôle

Traduit l'état courant du robot en deux pages affichées à l'écran :

- **Page bouche** (page 0) : bouche dessinée avec Pillow, imposée pendant une annonce
  vocale (`/robot/parole_en_cours`), et forcée juste après un passage du mode manuel
  vers le mode autonomie.
- **Page tableau de bord** (page 1) : mode de conduite, tension/courant des deux rails
  d'alimentation, consignes moteur gauche/droite réellement appliquées.

Les abonnements ne font que mettre à jour un état interne en mémoire ; un timer à
10 Hz est le seul endroit du nœud qui dessine à l'écran.

### Forme et animation de la page bouche

Deux rectangles à coins arrondis nets et concentriques, dessinés directement avec
Pillow sur l'écran complet 320 x 240 (pas de `GrilleTexte`), centre fixe (160, 140),
toujours dessinés tous les deux — l'intérieur ne disparaît jamais, même au repos.
Rayon de coin uniforme pour chaque rectangle : 0.55 x sa propre demi-hauteur
courante. Seules les dimensions suivent l'**ouverture** continue (0.0 à 1.0) ;
chaque rectangle garde sa couleur fixe à tout degré d'ouverture.

- Extérieur : demi-largeur interpolée entre 88 px (ouverture 0.0) et 112 px
  (ouverture 1.0), demi-hauteur interpolée entre 26 px et 40 px. Couleur fixe
  RVB (46, 87, 135).
- Intérieur : demi-largeur = demi-largeur de l'extérieur moins 15 px (marge fixe,
  suit donc automatiquement la largeur de l'extérieur), demi-hauteur interpolée
  entre 5 px (mince mais toujours visible) et 32 px. Couleur fixe RVB (22, 42, 65).
  L'intérieur grandit beaucoup plus que l'extérieur avec l'ouverture, surtout en
  hauteur, ce qui suggère une bouche qui s'ouvre plutôt qu'un simple agrandissement
  d'ensemble.

Animation pilotée par `/robot/parole_en_cours`, par transitions lissées (smoothstep)
d'une ouverture de départ vers une ouverture cible :

- faux : ouverture toujours ramenée à 0.0 (bouche aplatie) ;
- vrai : dès qu'une transition se termine, tirage d'une nouvelle transition — 88 %
  du temps vers une cible aléatoire entre 0.3 et 1.0 sur une durée aléatoire de
  65 à 130 ms, 12 % du temps vers 0.0 (courte pause de 45 à 85 ms, simule une
  respiration entre les mots). Le tirage évite un cycle mécanique et évoque une
  phrase parlée ;
- dès que `/robot/parole_en_cours` repasse à faux, une nouvelle transition vers 0.0
  démarre immédiatement en continuité depuis l'ouverture courante (départ = valeur
  au moment de la coupure, durée ~80 ms), sans attendre la fin de la transition
  interrompue : le retour au repos est rapide et fluide, jamais un saut brusque.

Le timer à 10 Hz ne retransmet à l'écran que si l'ouverture à afficher a changé
depuis le dernier tick. L'ouverture varie en continu, mais reste échantillonnée par
ce timer : la fluidité perçue est donc plafonnée à 10 images par seconde (décision
antérieure sur la boucle de rendu, hors de portée de cette page).

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

Intégré au lancement de production via `devastator.launch.yaml`
(`robot_devastator_bringup/config/affichage_lcd.yaml`). Pour un essai isolé, sans autre
nœud (tous les signaux ci-dessus peuvent être publiés à la main) :

```bash
ros2 run affichage_lcd affichage_lcd
```

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
# Page bouche imposée : le rectangle extérieur s'élargit et s'agrandit
# modérément, l'intérieur grandit beaucoup plus (surtout en hauteur), les deux
# couleurs restant chacune constantes tout au long du mouvement

ros2 topic pub --once /affichage/page_suivante std_msgs/msg/Empty '{}'
# Ignoré : la page reste sur la bouche tant que /robot/parole_en_cours est vrai

ros2 topic pub /robot/parole_en_cours std_msgs/msg/Bool '{data: false}' \
  --qos-durability transient_local --once
# Retour rapide et fluide au rectangle aplati (pas un saut brusque)

ros2 topic pub --once /affichage/page_suivante std_msgs/msg/Empty '{}'
# Fonctionne à nouveau : bascule vers la page 1
```

## Limites connues

- Une seule page de statut pour l'instant (page 1) ; le bouclage de
  `/affichage/page_suivante` n'alterne donc qu'entre les pages 0 et 1.
- L'ouverture de la bouche varie en continu, mais reste échantillonnée par le
  timer d'affichage à 10 Hz : les durées de transition tirées (65 à 130 ms,
  pauses 45 à 85 ms) ne sont donc respectées qu'à environ 100 ms près.
