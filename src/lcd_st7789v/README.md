# lcd_st7789v

Package **sans dépendance ROS 2** regroupant les deux couches basses de l'affichage
de Devastator, sur écran LCD Waveshare 2 pouces (contrôleur ST7789V, 240x320,
RGB565, SPI, écriture seule) :

| Module | Rôle |
|---|---|
| `pilote_st7789v` | Pilote bas niveau. Transmet à l'écran des images [Pillow](https://pillow.readthedocs.io/) déjà construites. Ne dessine rien lui-même. |
| `rendu_texte` | Grille de caractères façon terminal, avec rendu différentiel. Bâti au-dessus du pilote. |

Deux des trois niveaux de l'empilement d'affichage : le pilote, le rendu texte, puis
un futur package ROS 2. Les deux modules sont réutilisables tels quels sur un autre
projet.

## Pilote : interface publique

Classe `EcranSt7789v` (`lcd_st7789v.pilote_st7789v`) :

| Membre | Rôle |
|---|---|
| `EcranSt7789v(...)` | Ouvre le bus SPI, réclame les broches GPIO et initialise le contrôleur. Voir paramètres ci-dessous. |
| `afficher_image_pleine(image)` | Affiche une image Pillow en plein écran. L'image doit avoir exactement la taille effective de l'écran (`ecran.largeur`, `ecran.hauteur`), sinon `ValueError`. |
| `afficher_image_region(image, x, y)` | Affiche une image Pillow dans un rectangle dont le coin supérieur gauche est `(x, y)` et dont la taille est celle de l'image reçue. Lève `ValueError` si la région déborde de l'écran. |
| `regler_retroeclairage(intensite_pourcent)` | Règle l'intensité du rétroéclairage (0 à 100), par PWM logiciel. |
| `fermer()` | Libère le bus SPI et les broches GPIO. Idempotent, tolérant à une construction partiellement échouée. |
| `with EcranSt7789v(...) as ecran:` | Gestionnaire de contexte : appelle `fermer()` automatiquement, y compris en cas d'exception. **À préférer** à un appel manuel de `fermer()`. |

Paramètres du constructeur (valeurs par défaut = câblage validé sur Devastator, voir
`docs/connexions.md` du dépôt principal) :

| Paramètre | Défaut | Rôle |
|---|---|---|
| `bus_spi` | `0` | Bus SPI (`/dev/spidevX.Y`) |
| `peripherique_spi` | `0` | Périphérique SPI (CE0) |
| `broche_dc` | `25` | Broche donnée/commande (BCM) |
| `broche_rst` | `24` | Broche de reset matériel (BCM) |
| `broche_bl` | `12` | Broche de rétroéclairage, PWM logiciel (BCM) |
| `frequence_spi_hz` | `32_000_000` | Fréquence SPI. Valeur retenue après mesure sur le robot : 53 ms par plein écran, contre 172 ms à 8 MHz. Pour la modifier, procéder par paliers jusqu'à l'apparition d'artefacts à l'écran, puis redescendre d'un palier. |
| `frequence_pwm_bl_hz` | `1000` | Fréquence du PWM logiciel du rétroéclairage |
| `paysage` | `True` | Orientation logique fixée à la construction selon le montage physique : `True` = 320x240 (côté long à l'horizontal, montage actuel sur Devastator), `False` = 240x320 (orientation native du panneau) |
| `puce_gpio` | `0` | Numéro de puce GPIO lgpio (`/dev/gpiochipN`) |
| `taille_bloc_spi` | `4096` | Taille des blocs de transfert SPI |

## Rendu texte : interface publique

Classe `GrilleTexte` (`lcd_st7789v.rendu_texte`) : simule un terminal texte sur
l'écran. Une grille de cellules de taille fixe, chacune portant un caractère, une
couleur de texte et une couleur de fond indépendantes.

Le module conserve deux états en mémoire, l'état **voulu** et l'état **affiché**, et
ne retransmet que les cellules dont le contenu logique a changé — une cellule
modifiée, un appel à `afficher_image_region`. La comparaison porte sur le triplet
(caractère, couleur de texte, couleur de fond), jamais sur les pixels. Les cellules
adjacentes modifiées ne sont pas regroupées en un seul envoi.

Le module ne connaît rien à ROS 2, aux topics ni au sens de ce qu'il affiche. Il ne
construit pas le pilote : il en reçoit une instance déjà initialisée, et n'utilise
que `largeur`, `hauteur`, `afficher_image_region` et `afficher_image_pleine`.

### Résolution de la grille

Valeurs **mesurées** avec Pillow, pas choisies à l'avance :

| Mesure | Valeur |
|---|---|
| Police | DejaVu Sans Mono (`/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf`) |
| Taille | 16 points |
| Avance horizontale d'un caractère | 9.641 px, arrondie au pixel supérieur |
| Métriques verticales (ascendante + descendante) | 15 + 4 px |
| **Taille d'une cellule** | **10 x 19 px** |
| **Grille sur 320 x 240** | **32 colonnes x 12 lignes** (384 cellules) |
| Pixels inutilisés | 0 en largeur, 12 px en bas (12 x 19 = 228 sur 240) |

La cible indicative était d'environ 26 colonnes sur 15 lignes, ce qui supposait une
cellule au rapport largeur/hauteur d'environ 0.77, propre aux polices bitmap de
terminal (VGA 8x16). DejaVu Sans Mono est bien plus étroite — rapport 0.51, avance
de 0.602 em pour une hauteur de ligne de 1.164 em — et **aucune taille entière ne
donne 26 x 15 sans déformer les glyphes**. Autres tailles mesurées, si le besoin
change : 13 points donnent 40 x 14 (cellule 8 x 17), 19 points donnent 26 x 10
(cellule 12 x 23).

La bande de 12 px sous la dernière ligne n'appartient à aucune cellule : seul
`effacer()` la repeint.

### Méthodes

| Membre | Rôle |
|---|---|
| `GrilleTexte(ecran, taille_police=16, chemin_police=..., couleur_texte=BLANC, couleur_fond=NOIR)` | Mesure la police et en déduit la grille. Lève `FileNotFoundError` si le fichier de police est absent, `ValueError` si la police est trop grande pour l'écran. |
| `ecrire_caractere(colonne, ligne, caractere, couleur_texte=None, couleur_fond=None)` | Place un caractère dans l'état voulu. `IndexError` hors grille, `ValueError` si la chaîne ne fait pas exactement 1 caractère. |
| `ecrire_texte(colonne, ligne, texte, couleur_texte=None, couleur_fond=None)` | Écrit sur **une seule ligne**, sans passage à la ligne suivante. Retourne le nombre de caractères réellement écrits. |
| `effacer_cellule(colonne, ligne, couleur_fond=None)` | Vide une cellule de l'état voulu. |
| `effacer(couleur_fond=None)` | **Efface immédiatement tout l'écran** en un seul plein écran, et synchronise les deux états. |
| `rendre()` | Transmet les seules cellules changées. Retourne le nombre de cellules redessinées. |

Attributs publics calculés à la construction : `colonnes`, `lignes`,
`largeur_cellule`, `hauteur_cellule`.

Couleurs prédéfinies exportées par le module (triplets RVB) : `NOIR`, `BLANC`,
`ROUGE`, `VERT`, `BLEU`, `JAUNE`, `CYAN`, `MAGENTA`, `GRIS`.

### Bornes : erreur ou troncature

La distinction est volontaire :

- **position de départ hors grille** → `IndexError`. C'est une erreur de
  programmation, elle doit être bruyante ;
- **chaîne trop longue** → tronquée à la dernière colonne, sans exception. C'est un
  cas courant, signalé par la valeur de retour de `ecrire_texte`.

### Deux exceptions au principe « seul `rendre()` transmet à l'écran »

1. `effacer()` peint immédiatement l'écran entier. Un effacement cellule par cellule
   coûterait 384 appels au pilote au lieu d'un seul, et ne pourrait pas nettoyer la
   bande résiduelle du bas.
2. **Appeler `effacer()` en premier**, avant le premier `rendre()`. À l'allumage, le
   contenu de l'écran est inconnu : l'état affiché démarre donc à « inconnu » partout
   et un premier `rendre()` enverrait les 384 cellules vides une par une.

### Exemple minimal

```python
from lcd_st7789v.pilote_st7789v import EcranSt7789v
from lcd_st7789v.rendu_texte import GrilleTexte, NOIR, VERT, ROUGE

with EcranSt7789v() as ecran:
    ecran.regler_retroeclairage(80.0)
    grille = GrilleTexte(ecran)

    grille.effacer(NOIR)                             # etat de depart connu
    grille.ecrire_texte(0, 0, 'Batterie : 11.8 V', VERT)
    grille.rendre()                                  # 17 cellules envoyees

    grille.ecrire_caractere(11, 0, '9', ROUGE)       # 11.8 -> 19.8
    grille.rendre()                                  # 1 seule cellule envoyee
```

### Limites connues

- Aucun regroupement des cellules adjacentes modifiées : chaque cellule est un appel
  au pilote. À revoir seulement si un besoin réel apparaît.
- Aucun cache des glyphes déjà tracés : chaque cellule redessinée reconstruit son
  image. Le coût dominant est le SPI, pas Pillow.
- Pas de curseur, de défilement ni de retour à la ligne automatique : ce module gère
  une grille, pas un flux de texte.

## Dépendances

Bibliothèques imposées par le projet (voir `AGENTS.md`, section GPIO et SPI) :
`spidev` pour le bus SPI, `lgpio` pour les broches GPIO (y compris le PWM logiciel
du rétroéclairage), Pillow et `numpy` pour les images. Aucune autre bibliothèque
d'accès GPIO (`gpiozero`, `RPi.GPIO`, `pigpio`, `bcm2835`, `wiringPi`) n'est utilisée
ni ne doit être ajoutée : les mélanger provoque des conflits d'accès aux broches.

Le module `rendu_texte` n'ajoute aucune bibliothèque : il n'utilise que Pillow, déjà
requis par le pilote. Il exige en revanche la **police DejaVu Sans Mono**, livrée par
le paquet `fonts-dejavu-core`, présent d'office sur Ubuntu 24.04 (poste comme
Raspberry Pi). Son absence est détectée à la construction de `GrilleTexte`, avec un
message nommant le paquet à installer.

```bash
sudo apt install python3-spidev python3-lgpio python3-pil python3-numpy
sudo apt install fonts-dejavu-core
```

## Permissions requises

Aucune exécution en root. L'utilisateur qui lance le pilote doit appartenir aux
groupes `gpio` et `spi` :

```bash
sudo usermod -aG gpio,spi $USER
```

Ouvrir une nouvelle session (déconnexion/reconnexion SSH) pour que l'appartenance
aux groupes soit prise en compte.

## Essais directs sur le Raspberry Pi 4

Deux scripts autonomes à la racine de ce package, sans dépendance ROS 2 et sans
`colcon build` requis :

- `essai_pilote.py` : initialise l'écran, affiche une mire de couleurs plein écran en
  mesurant la durée du rafraîchissement, puis affiche une petite région et mesure
  également sa durée.
- `essai_rendu_texte.py` : construit le pilote et la grille, affiche une page d'état
  en plusieurs couleurs, modifie **une seule cellule** en mesurant le coût de ce
  rendu partiel, puis efface et redessine la grille complète en mesurant ce coût
  aussi. Il mesure enfin le pire cas (384 cellules changées), à comparer au plein
  écran du pilote : c'est ce rapport qui dit si le coût est dominé par le nombre
  d'appels ou par le volume de pixels.

**Règle d'exploitation impérative avant tout essai direct** : `lgpio` verrouille les
broches GPIO au niveau noyau. Si un lancement permanent du robot (ou tout autre
processus) détient déjà l'écran, l'ouverture des broches par ce script échoue.
Arrêter ce lancement avant l'essai :

```bash
# Si le robot tourne en lancement permanent (autre terminal), l'arrêter (Ctrl+C),
# puis vérifier qu'aucun nœud ne subsiste :
ros2 node list
```

Lancer ensuite l'essai :

```bash
cd ~/projets/robot_devastator_ws/src/lcd_st7789v
python3 essai_pilote.py
python3 essai_rendu_texte.py
```

Les deux scripts signalent explicitement les causes probables des échecs courants
(bibliothèque ou police manquante, permission refusée, broche déjà retenue par un
autre processus).

## Origine du code

La séquence d'initialisation du contrôleur ST7789V (réglages gamma compris), les
codes de commande, la logique de définition de la fenêtre d'adressage, la formule de
conversion RGB565 et la séquence de réinitialisation matérielle sont repris du code
de démonstration Waveshare (dépôt `LCD_Module_RPI_code`, licence MIT,
Copyright 2022 Waveshare Electronics) : ce sont des faits matériels du contrôleur et
du panneau, déjà validés sur le robot physique (après adaptation des broches RST et
BL au câblage réel). La structure de classe, la gestion des ressources, les
identifiants et l'interface publique sont propres à ce projet et n'ont pas
d'équivalent dans le code Waveshare, qui dépend de `gpiozero` (proscrit ici).

Un seul écart volontaire au code Waveshare, dans `_definir_fenetre` : la référence
décrémente uniquement l'octet bas de l'adresse de fin et laisse l'octet haut porter
la valeur non décrémentée. L'asymétrie est sans effet tant que la fin de fenêtre
n'est pas un multiple de 256, ce qui n'arrive jamais en plein écran (320 ou 240) ;
elle transmet en revanche 511 au lieu de 255 pour une fenêtre se terminant
exactement à 256. Le pilote convertit donc la borne exclusive en adresse inclusive
avant de séparer les deux octets.

## Limites connues du pilote

- Orientation `paysage=True` validée sur le matériel réel avec MADCTL = 0xA0
  (voir la constante `_MADCTL_PAYSAGE`). La valeur 0x70 reprise du code Waveshare
  produisait une image inversée à 180° ; jamais testée par Waveshare lui-même avec
  du contenu asymétrique.
- Écriture seule : aucune lecture d'état du panneau (MISO non câblé).
