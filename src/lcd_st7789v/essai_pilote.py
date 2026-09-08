#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Essai autonome du pilote `lcd_st7789v`, sans dépendance ROS 2.

Ce script initialise l'écran, affiche une image plein écran en mesurant la durée du
rafraîchissement, puis affiche une petite région et mesure également sa durée. Il ne
nécessite ni `colcon build` ni sourcing ROS 2 : il ajoute lui-même le dossier du
package à son chemin d'import, pour rester exécutable juste après un transfert du
dépôt sur le Raspberry Pi 4 (`python3 essai_pilote.py`).

ATTENTION avant de lancer cet essai : lgpio verrouille les broches GPIO au niveau
noyau. Si un processus tient déjà l'écran (par exemple un lancement permanent du
robot), l'ouverture des broches échoue ici. Arrêter ce processus avant l'essai
(voir le README de ce package).
"""

import sys
import time
from pathlib import Path

# Rend le package importable sans build ni sourcing : ce fichier vit à la racine
# du package `lcd_st7789v`, le sous-dossier de même nom contient le module pilote.
_RACINE_PACKAGE = Path(__file__).resolve().parent
if str(_RACINE_PACKAGE) not in sys.path:
    sys.path.insert(0, str(_RACINE_PACKAGE))

try:
    from PIL import Image, ImageDraw
except ImportError as erreur:
    print(f"Bibliothèque Pillow manquante ({erreur}).")
    print('Installer avec : sudo apt install python3-pil')
    sys.exit(1)

try:
    from lcd_st7789v.pilote_st7789v import EcranSt7789v
except ImportError as erreur:
    print(f"Impossible d'importer le pilote ({erreur}).")
    print(
        'Vérifier que spidev, lgpio et numpy sont installés :\n'
        '  sudo apt install python3-spidev python3-lgpio python3-numpy'
    )
    sys.exit(1)


def construire_image_plein_ecran(largeur: int, hauteur: int) -> Image.Image:
    """
    Construit une mire de bandes de couleur plein écran.

    Une mire à bandes primaires/secondaires est le test de référence pour
    valider une conversion RGB565 : toute inversion de canal ou de demi-octet se
    voit immédiatement à l'œil (bande de la mauvaise couleur ou mal positionnée).
    """
    image = Image.new('RGB', (largeur, hauteur))
    dessin = ImageDraw.Draw(image)
    couleurs = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255),
        (0, 0, 0), (0, 255, 255), (255, 0, 255), (255, 255, 0),
    ]
    largeur_bande = largeur / len(couleurs)
    for indice, couleur in enumerate(couleurs):
        x_debut = round(indice * largeur_bande)
        x_fin = round((indice + 1) * largeur_bande)
        dessin.rectangle([x_debut, 0, x_fin - 1, hauteur - 1], fill=couleur)
    return image


def construire_image_region(largeur: int, hauteur: int) -> Image.Image:
    """Construit une petite image de contraste pour le test d'affichage en région."""
    image = Image.new('RGB', (largeur, hauteur), color=(255, 128, 0))
    dessin = ImageDraw.Draw(image)
    dessin.rectangle([0, 0, largeur - 1, hauteur - 1], outline=(0, 0, 0), width=2)
    return image


def main() -> int:
    print("Essai du pilote lcd_st7789v (écran Waveshare 2 pouces, contrôleur ST7789V)")

    try:
        with EcranSt7789v() as ecran:
            print(
                f'Écran initialisé avec succès : {ecran.largeur} x {ecran.hauteur} '
                '(orientation paysage par défaut)'
            )

            ecran.regler_retroeclairage(80.0)
            print('Rétroéclairage réglé à 80 %.')

            image_pleine = construire_image_plein_ecran(ecran.largeur, ecran.hauteur)
            debut = time.perf_counter()
            ecran.afficher_image_pleine(image_pleine)
            duree_ms = (time.perf_counter() - debut) * 1000
            print(f'Affichage plein écran : {duree_ms:.1f} ms')

            largeur_region, hauteur_region = 80, 60
            x_region = (ecran.largeur - largeur_region) // 2
            y_region = (ecran.hauteur - hauteur_region) // 2
            image_region = construire_image_region(largeur_region, hauteur_region)
            debut = time.perf_counter()
            ecran.afficher_image_region(image_region, x_region, y_region)
            duree_ms = (time.perf_counter() - debut) * 1000
            print(
                f'Affichage région {largeur_region}x{hauteur_region} '
                f'à ({x_region}, {y_region}) : {duree_ms:.1f} ms'
            )

            print('Essai terminé avec succès.')
            print(
                "Fermeture : le rétroéclairage s'éteint et les broches GPIO sont "
                'libérées (comportement normal de fin de contexte).'
            )
        return 0

    except PermissionError as erreur:
        print(f'Permission refusée : {erreur}')
        print(
            "L'utilisateur courant doit appartenir aux groupes gpio et spi "
            '(sudo usermod -aG gpio,spi $USER), puis ouvrir une nouvelle session.'
        )
        return 1

    except KeyboardInterrupt:
        print('\nEssai interrompu par Ctrl+C.')
        return 1

    except Exception as erreur:  # noqa: BLE001 - dernier filet avant un message utilisateur
        print(f"Échec de l'essai : {type(erreur).__name__}: {erreur}")
        print(
            "Cause probable si l'erreur mentionne une broche déjà retenue "
            "(gpio busy / already requested) : un lancement permanent du robot "
            "tient déjà l'écran. L'arrêter, puis relancer cet essai."
        )
        return 1


if __name__ == '__main__':
    sys.exit(main())
