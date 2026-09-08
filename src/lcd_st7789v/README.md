# lcd_st7789v

Pilote bas niveau, **sans dépendance ROS 2**, de l'écran LCD Waveshare 2 pouces
(contrôleur ST7789V, 240x320, RGB565, SPI, écriture seule). Couche la plus basse
d'un empilement à trois niveaux : ce pilote, un futur module de rendu texte, puis un
futur package ROS 2. Réutilisable tel quel sur un autre projet.

Le pilote ne dessine rien (pas de texte, de ligne, de forme ni de couleur) : il
reçoit des images [Pillow](https://pillow.readthedocs.io/) déjà construites par
l'appelant et les transmet à l'écran.

## Interface publique

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
| `frequence_spi_hz` | `8_000_000` | Fréquence SPI. Prudente par défaut : pour l'augmenter, procéder par paliers (8 -> 16 -> 24 MHz...) jusqu'à l'apparition d'artefacts à l'écran, puis redescendre d'un palier. |
| `frequence_pwm_bl_hz` | `1000` | Fréquence du PWM logiciel du rétroéclairage |
| `paysage` | `True` | Orientation logique fixée à la construction selon le montage physique : `True` = 320x240 (côté long à l'horizontal, montage actuel sur Devastator), `False` = 240x320 (orientation native du panneau) |
| `puce_gpio` | `0` | Numéro de puce GPIO lgpio (`/dev/gpiochipN`) |
| `taille_bloc_spi` | `4096` | Taille des blocs de transfert SPI |

## Dépendances

Bibliothèques imposées par le projet (voir `AGENTS.md`, section GPIO et SPI) :
`spidev` pour le bus SPI, `lgpio` pour les broches GPIO (y compris le PWM logiciel
du rétroéclairage), Pillow et `numpy` pour les images. Aucune autre bibliothèque
d'accès GPIO (`gpiozero`, `RPi.GPIO`, `pigpio`, `bcm2835`, `wiringPi`) n'est utilisée
ni ne doit être ajoutée : les mélanger provoque des conflits d'accès aux broches.

```bash
sudo apt install python3-spidev python3-lgpio python3-pil python3-numpy
```

## Permissions requises

Aucune exécution en root. L'utilisateur qui lance le pilote doit appartenir aux
groupes `gpio` et `spi` :

```bash
sudo usermod -aG gpio,spi $USER
```

Ouvrir une nouvelle session (déconnexion/reconnexion SSH) pour que l'appartenance
aux groupes soit prise en compte.

## Essai direct sur le Raspberry Pi 4

`essai_pilote.py`, à la racine de ce package, est un script autonome (aucune
dépendance ROS 2, aucun `colcon build` requis) : il initialise l'écran, affiche une
mire de couleurs plein écran en mesurant la durée du rafraîchissement, puis affiche
une petite région et mesure également sa durée.

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
```

Le script signale explicitement les causes probables des échecs courants
(bibliothèque manquante, permission refusée, broche déjà retenue par un autre
processus).

## Origine du code

La séquence d'initialisation du contrôleur ST7789V (réglages gamma compris), les
codes de commande, la logique de définition de la fenêtre d'adressage, la formule de
conversion RGB565 et la séquence de réinitialisation matérielle sont repris tels
quels du code de démonstration Waveshare (dépôt `LCD_Module_RPI_code`, licence MIT,
Copyright 2022 Waveshare Electronics) : ce sont des faits matériels du contrôleur et
du panneau, déjà validés sur le robot physique (après adaptation des broches RST et
BL au câblage réel). La structure de classe, la gestion des ressources, les
identifiants et l'interface publique sont propres à ce projet et n'ont pas
d'équivalent dans le code Waveshare, qui dépend de `gpiozero` (proscrit ici).

## Limites connues

- Orientation `paysage=True` (320x240, rotation MADCTL) non encore validée sur le
  matériel réel : seule l'orientation native (`paysage=False`) correspond au sens
  déjà exercé dans la démonstration Waveshare sur ce robot. À confirmer au premier
  essai.
- Écriture seule : aucune lecture d'état du panneau (MISO non câblé).
