# -*- coding: utf-8 -*-
"""
Rendu de texte en grille de caractères sur un écran piloté par `pilote_st7789v`.

Ce module simule un terminal texte : une grille de cellules de taille fixe, chacune
portant un caractère, une couleur de texte et une couleur de fond indépendantes. Il
conserve en mémoire l'état voulu et l'état réellement affiché, et ne retransmet à
l'écran que les cellules dont le contenu logique a changé.

Deuxième couche d'un empilement à trois niveaux : le pilote, ce module, puis un
futur package ROS 2. Comme le pilote, il ne dépend d'aucun élément propre à un robot
ni à ROS 2, et ignore tout du sens de ce qu'on lui fait afficher : il ne connaît que
la grille et la comparaison d'état.

Couplage volontairement faible avec le pilote : ce module n'en crée jamais
d'instance, il en reçoit une déjà initialisée et n'utilise que `largeur`, `hauteur`,
`afficher_image_region` et `afficher_image_pleine`. Tout objet offrant ces quatre
membres convient.

Dépendances : Pillow seulement (police, mesure et tracé des caractères).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:  # Import réservé à l'analyse statique : à l'exécution, ce module
    # n'a besoin ni de lgpio ni de spidev, ce qui le rend testable hors Raspberry Pi.
    from lcd_st7789v.pilote_st7789v import EcranSt7789v

# Type d'une couleur : triplet RVB de 0 à 255, converti en RGB565 par le pilote.
Couleur = tuple[int, int, int]

# --- Couleurs usuelles, pour éviter des triplets littéraux dispersés ---
NOIR: Final[Couleur] = (0, 0, 0)
BLANC: Final[Couleur] = (255, 255, 255)
ROUGE: Final[Couleur] = (255, 0, 0)
VERT: Final[Couleur] = (0, 255, 0)
BLEU: Final[Couleur] = (0, 0, 255)
JAUNE: Final[Couleur] = (255, 255, 0)
CYAN: Final[Couleur] = (0, 255, 255)
MAGENTA: Final[Couleur] = (255, 0, 255)
GRIS: Final[Couleur] = (128, 128, 128)

# Police à chasse fixe livrée par le paquet Ubuntu `fonts-dejavu-core`, présent
# d'office sur Ubuntu 24.04 (poste comme Raspberry Pi). Aucune installation
# supplémentaire n'est requise, mais l'existence du fichier est vérifiée à la
# construction plutôt que laissée à l'erreur générique de Pillow.
CHEMIN_POLICE_DEJAVU_MONO: Final[str] = (
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
)

# Taille en points donnant 32 colonnes sur 12 lignes en 320 x 240 (voir le calcul
# détaillé dans la docstring de `GrilleTexte.__init__`).
TAILLE_POLICE_DEFAUT: Final[int] = 16


@dataclass(frozen=True)
class Cellule:
    """
    Contenu logique d'une cellule de la grille.

    Immuable et comparable par valeur : c'est précisément ce que compare `rendre()`
    pour décider si une cellule doit être retransmise. La comparaison porte donc sur
    le caractère et ses deux couleurs, jamais sur les pixels produits.
    """

    caractere: str
    couleur_texte: Couleur
    couleur_fond: Couleur


class GrilleTexte:
    """
    Grille de caractères affichée sur un écran, avec rendu différentiel.

    Les méthodes d'écriture ne touchent jamais l'écran : elles ne modifient que
    l'état voulu en mémoire. Seuls `rendre()` et `effacer()` transmettent au pilote.

    Le nombre de colonnes et de lignes n'est pas choisi : il est déduit des
    métriques réelles de la police et de la taille de l'écran (voir `__init__`).
    """

    def __init__(
        self,
        ecran: 'EcranSt7789v',
        taille_police: int = TAILLE_POLICE_DEFAUT,
        chemin_police: str = CHEMIN_POLICE_DEJAVU_MONO,
        couleur_texte: Couleur = BLANC,
        couleur_fond: Couleur = NOIR,
    ) -> None:
        """
        Mesure la police, en déduit la grille et prépare l'état interne.

        `ecran` doit être une instance de pilote déjà initialisée : ce module ne la
        construit pas et ne la ferme pas, il ne fait que s'en servir.

        Calcul de la grille, avec DejaVu Sans Mono à 16 points sur 320 x 240 :

        - avance horizontale d'un caractère (chasse fixe) : 9.641 px, arrondie au
          pixel supérieur, d'où une cellule de 10 px de large ;
        - métriques verticales : 15 px au-dessus de la ligne de base, 4 px en
          dessous, d'où une cellule de 19 px de haut ;
        - grille : 320 // 10 = 32 colonnes, 240 // 19 = 12 lignes.

        La cible indicative était d'environ 26 colonnes sur 15 lignes, ce qui
        supposait une cellule au rapport largeur/hauteur d'environ 0.77, propre aux
        polices bitmap de terminal. DejaVu Sans Mono est bien plus étroite (rapport
        0.51) : aucune taille entière ne donne 26 x 15 sans déformer les glyphes. La
        taille 16 privilégie la lisibilité ; 13 points donneraient 40 x 14.

        La division entière laisse 12 px inutilisés au bas de l'écran (12 x 19 = 228
        sur 240) et aucun sur la largeur. Cette bande n'appartient à aucune cellule :
        seul `effacer()` la repeint.
        """
        # Échec explicite si la police manque, plutôt qu'un OSError générique de
        # Pillow qui n'indiquerait pas quel paquet installer.
        if not os.path.isfile(chemin_police):
            raise FileNotFoundError(
                f'Police introuvable : {chemin_police}. Sur Ubuntu, installer le '
                'paquet fonts-dejavu-core (sudo apt install fonts-dejavu-core).'
            )

        self._ecran = ecran
        self._police = ImageFont.truetype(chemin_police, taille_police)
        self.couleur_texte = couleur_texte
        self.couleur_fond = couleur_fond

        # Mesures réelles de la police : la chasse est fixe, donc l'avance d'un
        # caractère quelconque vaut pour tous. Arrondie vers le haut pour que le
        # glyphe le plus large tienne toujours dans la cellule.
        avance = self._police.getlength('M')
        ascendante, descendante = self._police.getmetrics()
        self.largeur_cellule: int = math.ceil(avance)
        self.hauteur_cellule: int = ascendante + descendante

        self.colonnes: int = ecran.largeur // self.largeur_cellule
        self.lignes: int = ecran.hauteur // self.hauteur_cellule
        if self.colonnes < 1 or self.lignes < 1:
            raise ValueError(
                f'Police de taille {taille_police} trop grande pour un écran '
                f'{ecran.largeur} x {ecran.hauteur} : cellule de '
                f'{self.largeur_cellule} x {self.hauteur_cellule} px.'
            )

        # Recentrage horizontal du glyphe dans la cellule, l'avance réelle étant
        # fractionnaire alors que la cellule est entière. Vaut 0 px à 16 points
        # (écart de 0.36 px) ; la formule reste utile pour d'autres tailles.
        self._decalage_x: int = round((self.largeur_cellule - avance) / 2)

        # Deux états distincts. `_voulu` est modifié par les méthodes d'écriture ;
        # `_affiche` reflète ce que l'écran montre réellement. Il démarre à None
        # partout car le contenu de l'écran est inconnu à l'allumage : le premier
        # `rendre()` redessine donc toute la grille, sans rien supposer.
        vide = Cellule(' ', couleur_texte, couleur_fond)
        self._voulu: list[list[Cellule]] = [
            [vide] * self.colonnes for _ in range(self.lignes)
        ]
        self._affiche: list[list[Cellule | None]] = [
            [None] * self.colonnes for _ in range(self.lignes)
        ]

    # --- Méthodes publiques ---

    def ecrire_caractere(
        self,
        colonne: int,
        ligne: int,
        caractere: str,
        couleur_texte: Couleur | None = None,
        couleur_fond: Couleur | None = None,
    ) -> None:
        """
        Place un caractère dans une cellule de l'état voulu.

        Rien n'est transmis à l'écran ici : il faut appeler `rendre()`. Une position
        hors de la grille lève `IndexError` ; une chaîne dont la longueur n'est pas
        exactement 1 lève `ValueError`.
        """
        self._valider_position(colonne, ligne)
        if len(caractere) != 1:
            raise ValueError(
                f'Un seul caractère attendu, reçu {len(caractere)} : {caractere!r}'
            )

        self._voulu[ligne][colonne] = Cellule(
            caractere,
            self.couleur_texte if couleur_texte is None else couleur_texte,
            self.couleur_fond if couleur_fond is None else couleur_fond,
        )

    def ecrire_texte(
        self,
        colonne: int,
        ligne: int,
        texte: str,
        couleur_texte: Couleur | None = None,
        couleur_fond: Couleur | None = None,
    ) -> int:
        """
        Écrit une chaîne sur une seule ligne, à partir de (colonne, ligne).

        La chaîne ne passe jamais à la ligne suivante : ce qui dépasse la dernière
        colonne est tronqué. La valeur retournée est le nombre de caractères
        réellement écrits, ce qui permet à l'appelant de détecter une troncature.

        La distinction est volontaire : une position de départ hors grille est une
        erreur de programmation et lève `IndexError`, alors qu'une chaîne trop
        longue est un cas courant, traité par troncature signalée par le retour.
        """
        self._valider_position(colonne, ligne)

        place_restante = self.colonnes - colonne
        texte_tronque = texte[:place_restante]
        for decalage, caractere in enumerate(texte_tronque):
            self.ecrire_caractere(
                colonne + decalage, ligne, caractere, couleur_texte, couleur_fond
            )

        return len(texte_tronque)

    def effacer_cellule(
        self, colonne: int, ligne: int, couleur_fond: Couleur | None = None
    ) -> None:
        """
        Vide une cellule de l'état voulu, en lui donnant une couleur de fond.

        Comme les méthodes d'écriture, ne transmet rien à l'écran avant `rendre()`.
        """
        self.ecrire_caractere(colonne, ligne, ' ', None, couleur_fond)

    def effacer(self, couleur_fond: Couleur | None = None) -> None:
        """
        Efface immédiatement tout l'écran à une couleur de fond unie.

        Exception assumée au principe « seul `rendre()` transmet à l'écran », pour
        deux raisons concrètes :

        - un effacement cellule par cellule coûterait un appel au pilote par
          cellule, soit 384 transferts au lieu d'un seul ;
        - la bande de pixels sous la dernière ligne, que la division entière laisse
          hors grille, n'appartient à aucune cellule et ne peut être nettoyée que
          par un tracé plein écran.

        Les deux états sont mis à jour ensemble : l'écran étant réellement uni, le
        `rendre()` suivant ne redessine que les cellules effectivement réécrites.
        """
        fond = self.couleur_fond if couleur_fond is None else couleur_fond

        image = Image.new('RGB', (self._ecran.largeur, self._ecran.hauteur), fond)
        self._ecran.afficher_image_pleine(image)

        vide = Cellule(' ', self.couleur_texte, fond)
        for ligne in range(self.lignes):
            for colonne in range(self.colonnes):
                self._voulu[ligne][colonne] = vide
                self._affiche[ligne][colonne] = vide

    def rendre(self) -> int:
        """
        Transmet à l'écran les seules cellules dont le contenu logique a changé.

        Retourne le nombre de cellules redessinées, utile pour mesurer le coût réel
        d'un rafraîchissement partiel.

        L'état affiché n'est mis à jour qu'après un envoi réussi : si le pilote lève
        une exception, la cellule reste marquée comme différente et sera retentée au
        `rendre()` suivant, sans que l'état en mémoire ne mente sur l'écran.
        """
        redessinees = 0

        for ligne in range(self.lignes):
            for colonne in range(self.colonnes):
                cellule = self._voulu[ligne][colonne]
                if cellule == self._affiche[ligne][colonne]:
                    continue

                self._dessiner_cellule(colonne, ligne, cellule)
                self._affiche[ligne][colonne] = cellule
                redessinees += 1

        return redessinees

    # --- Méthodes privées utilitaires ---

    def _valider_position(self, colonne: int, ligne: int) -> None:
        """Lève `IndexError` si la position sort de la grille."""
        if not 0 <= colonne < self.colonnes or not 0 <= ligne < self.lignes:
            raise IndexError(
                f'Position ({colonne}, {ligne}) hors de la grille '
                f'{self.colonnes} x {self.lignes}'
            )

    def _dessiner_cellule(self, colonne: int, ligne: int, cellule: Cellule) -> None:
        """
        Construit l'image d'une cellule et la transmet au pilote.

        L'image fait exactement la taille de cellule calculée, comme l'exige la
        vérification stricte des dimensions de `afficher_image_region`.

        Le tracé se fait en (decalage_x, 0) avec l'ancrage Pillow par défaut d'une
        police TrueType, qui aligne le haut de l'ascendante sur l'origine. La
        hauteur de cellule valant ascendante + descendante, tous les glyphes tiennent
        et partagent la même ligne de base d'une cellule à l'autre.
        """
        image = Image.new(
            'RGB', (self.largeur_cellule, self.hauteur_cellule), cellule.couleur_fond
        )

        # L'espace ne produit aucun pixel : inutile de solliciter le moteur de rendu.
        if cellule.caractere != ' ':
            dessin = ImageDraw.Draw(image)
            dessin.text(
                (self._decalage_x, 0),
                cellule.caractere,
                font=self._police,
                fill=cellule.couleur_texte,
            )

        self._ecran.afficher_image_region(
            image, colonne * self.largeur_cellule, ligne * self.hauteur_cellule
        )
