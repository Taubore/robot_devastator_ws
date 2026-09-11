#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Essai autonome du module de rendu texte `rendu_texte`, sans dépendance ROS 2.

Ce script construit le pilote et la grille de texte, affiche quelques lignes de
couleurs différentes, modifie une seule cellule en mesurant le coût de ce rendu
partiel, puis efface et redessine la grille complète en mesurant ce coût aussi. Il
ne nécessite ni `colcon build` ni sourcing ROS 2 : il ajoute lui-même le dossier du
package à son chemin d'import (`python3 essai_rendu_texte.py`).

Les mesures sont l'objet réel de cet essai. Le rendu différentiel ne vaut que si le
coût d'une cellule est très inférieur à celui d'un plein écran : le script affiche
donc aussi le coût moyen par cellule, à comparer aux 53 ms d'un plein écran mesurés
par `essai_pilote.py` à 32 MHz.

ATTENTION avant de lancer cet essai : lgpio verrouille les broches GPIO au niveau
noyau. Si un processus tient déjà l'écran (par exemple un lancement permanent du
robot), l'ouverture des broches échoue ici. Arrêter ce processus avant l'essai
(voir le README de ce package).
"""

import sys
import time
from pathlib import Path

# Rend le package importable sans build ni sourcing : ce fichier vit à la racine
# du package `lcd_st7789v`, le sous-dossier de même nom contient les modules.
_RACINE_PACKAGE = Path(__file__).resolve().parent
if str(_RACINE_PACKAGE) not in sys.path:
    sys.path.insert(0, str(_RACINE_PACKAGE))

try:
    from lcd_st7789v.pilote_st7789v import EcranSt7789v
    from lcd_st7789v.rendu_texte import (
        BLANC, CYAN, GRIS, JAUNE, NOIR, ROUGE, VERT, GrilleTexte,
    )
except ImportError as erreur:
    print(f"Impossible d'importer le pilote ou le module de rendu texte ({erreur}).")
    print(
        'Vérifier que les dépendances sont installées :\n'
        '  sudo apt install python3-spidev python3-lgpio python3-numpy python3-pil\n'
        '  sudo apt install fonts-dejavu-core'
    )
    sys.exit(1)


def remplir_page_demonstration(grille: GrilleTexte) -> None:
    """
    Remplit l'état voulu avec une page d'état plausible, en plusieurs couleurs.

    Aucun envoi à l'écran ici : les méthodes d'écriture ne touchent que la mémoire.
    Le tracé n'a lieu qu'au `rendre()` appelé par `main`.
    """
    grille.ecrire_texte(0, 0, 'DEVASTATOR', JAUNE)
    grille.ecrire_texte(0, 1, '-' * grille.colonnes, GRIS)

    grille.ecrire_texte(0, 3, 'Batterie  : 11.8 V', VERT)
    grille.ecrire_texte(0, 4, 'Courant   : 0.42 A', VERT)
    grille.ecrire_texte(0, 5, 'Sonar     : 0.85 m', CYAN)
    grille.ecrire_texte(0, 6, 'Moteurs   : arretes', ROUGE)

    # Ligne d'accents et de symboles : contrôle visuel que les glyphes accentués
    # ne sont pas rognés en haut de cellule (É, à) ni en bas (ç, µ).
    grille.ecrire_texte(0, 8, 'Éteint à 42 °C ç µ Ω', BLANC)

    # Ligne inversée : couleur de fond différente sur toute la largeur, pour
    # vérifier que chaque cellule peint bien son propre fond.
    grille.ecrire_texte(0, 10, ' ETAT : PRET '.ljust(grille.colonnes), NOIR, VERT)


def main() -> int:
    """
    Déroule l'essai complet et retourne le code de sortie du script.

    Retourne 0 si l'essai est allé au bout, 1 sur toute erreur : le message
    d'échec nomme alors la cause probable plutôt que de laisser une trace brute.
    """
    print('Essai du module de rendu texte lcd_st7789v.rendu_texte')

    try:
        with EcranSt7789v() as ecran:
            print(f'Écran initialisé : {ecran.largeur} x {ecran.hauteur}')
            ecran.regler_retroeclairage(80.0)

            grille = GrilleTexte(ecran)
            cellules_totales = grille.colonnes * grille.lignes
            print(
                f'Grille : {grille.colonnes} colonnes x {grille.lignes} lignes, '
                f'cellule de {grille.largeur_cellule} x {grille.hauteur_cellule} px '
                f'({cellules_totales} cellules)'
            )
            # Rappel du calcul : la division entière laisse une bande inutilisée en
            # bas d'écran, que seul `effacer()` repeint.
            reste_bas = ecran.hauteur - grille.lignes * grille.hauteur_cellule
            print(f'Bande résiduelle sous la dernière ligne : {reste_bas} px')

            # --- Effacement initial : l'écran est dans un état inconnu ---
            # Sans cet appel, le premier rendre() enverrait les 384 cellules vides
            # une par une, faute de savoir ce que l'écran affiche déjà.
            debut = time.perf_counter()
            grille.effacer(NOIR)
            duree_effacement_ms = (time.perf_counter() - debut) * 1000
            print(f'\nEffacement initial (un seul plein écran) : {duree_effacement_ms:.1f} ms')

            # --- Affichage de la page de démonstration ---
            remplir_page_demonstration(grille)
            debut = time.perf_counter()
            cellules = grille.rendre()
            duree_page_ms = (time.perf_counter() - debut) * 1000
            print(
                f'Page de démonstration : {cellules} cellules redessinées en '
                f'{duree_page_ms:.1f} ms ({duree_page_ms / max(cellules, 1):.2f} ms/cellule)'
            )

            # --- Rendu partiel : une seule cellule modifiée ---
            # Coeur de l'essai : c'est ce coût qui décide si une page d'état peut
            # être rafraîchie plusieurs fois par seconde.
            grille.ecrire_caractere(12, 3, '9', ROUGE)
            debut = time.perf_counter()
            cellules = grille.rendre()
            duree_cellule_ms = (time.perf_counter() - debut) * 1000
            print(
                f'\nRendu partiel d\'une seule cellule : {cellules} cellule en '
                f'{duree_cellule_ms:.2f} ms'
            )

            # Un rendre() sans modification ne doit rien envoyer : vérifie que la
            # comparaison d'état fonctionne, et donne le coût du seul parcours.
            debut = time.perf_counter()
            cellules = grille.rendre()
            duree_vide_ms = (time.perf_counter() - debut) * 1000
            print(
                f'Rendu sans modification : {cellules} cellule en {duree_vide_ms:.2f} ms '
                '(parcours de la grille seul, aucun envoi SPI)'
            )

            time.sleep(5.0)

            # --- Effacement puis redessin complet ---
            debut = time.perf_counter()
            grille.effacer(NOIR)
            remplir_page_demonstration(grille)
            cellules = grille.rendre()
            duree_complet_ms = (time.perf_counter() - debut) * 1000
            print(
                f'\nEffacement + redessin complet : {cellules} cellules en '
                f'{duree_complet_ms:.1f} ms'
            )

            # --- Pire cas : toutes les cellules changent ---
            # Sans effacement préalable, donc 384 envois individuels. Sert de borne
            # supérieure et de point de comparaison avec le plein écran du pilote.
            for ligne in range(grille.lignes):
                grille.ecrire_texte(0, ligne, '#' * grille.colonnes, GRIS, NOIR)
            debut = time.perf_counter()
            cellules = grille.rendre()
            duree_pire_ms = (time.perf_counter() - debut) * 1000
            print(
                f'Pire cas ({cellules} cellules changées, aucun regroupement) : '
                f'{duree_pire_ms:.1f} ms '
                f'({duree_pire_ms / max(cellules, 1):.2f} ms/cellule)'
            )
            print(
                'À comparer aux ~53 ms d\'un plein écran mesurées par essai_pilote.py : '
                'si le pire cas est nettement plus lent, le coût est dominé par le '
                'nombre d\'appels au pilote, pas par le volume de pixels transmis.'
            )

            time.sleep(2.0)
            grille.effacer(NOIR)

            print('\nEssai terminé avec succès.')
            print(
                "Fermeture : le rétroéclairage s'éteint et les broches GPIO sont "
                'libérées (comportement normal de fin de contexte).'
            )
        return 0

    except FileNotFoundError as erreur:
        print(f'Fichier introuvable : {erreur}')
        print('Si le message concerne la police : sudo apt install fonts-dejavu-core')
        return 1

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
