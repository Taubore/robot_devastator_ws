# -*- coding: utf-8 -*-
"""
Nœud ROS 2 d'affichage sur l'écran LCD, troisième couche au-dessus de `lcd_st7789v`.

Aucun accès matériel direct : seules `EcranSt7789v` et `GrilleTexte` touchent au SPI
et aux GPIO. Les abonnements ne font que mettre à jour un état interne. Un timer à
10 Hz lit cet état et décide seul de ce qui est affiché, sur deux pages : la page 0
(bouche, affichée pendant la parole ou juste après un passage en autonomie) et la
page 1 (tableau de bord : mode, alimentation, consignes moteur).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Final

from commun.msg import ConsigneMoteurs
from lcd_st7789v.pilote_st7789v import EcranSt7789v
from lcd_st7789v.rendu_texte import CYAN, GrilleTexte, GRIS, JAUNE, NOIR, VERT
from PIL import Image, ImageDraw
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.time import Time
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, Empty, String

NB_PAGES: Final[int] = 2
PAGE_BOUCHE: Final[int] = 0
PAGE_TABLEAU_BORD: Final[int] = 1

TEXTE_INCONNU: Final[str] = '--'


# Centre fixe, maquette validée hors code. Deux rectangles à coins arrondis nets
# et concentriques, toujours dessinés tous les deux, chacun dans une couleur fixe :
# seules leurs dimensions suivent l'ouverture, jamais leur teinte.
CENTRE_BOUCHE_X: Final[int] = 160
CENTRE_BOUCHE_Y: Final[int] = 140

DEMI_LARGEUR_EXTERIEUR_BOUCHE_MIN: Final[float] = 88.0
DEMI_LARGEUR_EXTERIEUR_BOUCHE_MAX: Final[float] = 112.0
DEMI_HAUTEUR_EXTERIEUR_BOUCHE_MIN: Final[float] = 26.0
DEMI_HAUTEUR_EXTERIEUR_BOUCHE_MAX: Final[float] = 40.0
COULEUR_EXTERIEUR_BOUCHE: Final[tuple[int, int, int]] = (46, 87, 135)

MARGE_INTERIEUR_BOUCHE: Final[float] = 15.0
DEMI_HAUTEUR_INTERIEUR_BOUCHE_MIN: Final[float] = 5.0
DEMI_HAUTEUR_INTERIEUR_BOUCHE_MAX: Final[float] = 32.0
COULEUR_INTERIEUR_BOUCHE: Final[tuple[int, int, int]] = (22, 42, 65)

# Rectangle à coins arrondis net et symétrique : rayon de coin uniforme,
# proportionnel à la demi-hauteur de la forme concernée.
FACTEUR_RAYON_COIN_BOUCHE: Final[float] = 0.55
NB_POINTS_PAR_COIN_BOUCHE: Final[int] = 10

# Animation : ouverture continue (0.0 à 1.0), interpolée par transitions lissées
# (smoothstep) plutôt qu'un tirage entre paliers fixes.
PLAGE_CIBLE_OUVERTURE_BOUCHE: Final[tuple[float, float]] = (0.3, 1.0)
PLAGE_DUREE_TIRAGE_S: Final[tuple[float, float]] = (0.065, 0.130)
PLAGE_DUREE_PAUSE_RESPIRATION_S: Final[tuple[float, float]] = (0.045, 0.085)
PROBABILITE_PAUSE_RESPIRATION: Final[float] = 0.12
DUREE_TRANSITION_ARRET_S: Final[float] = 0.080


@dataclass
class EtatMesure:
    """Dernière tension et courant reçus d'un rail, avec l'instant de réception."""

    tension_v: float = 0.0
    courant_a: float = 0.0
    horodatage_reception: Time | None = None


class AffichageLcd(Node):
    """Affiche l'état du robot sur l'écran LCD, sans jamais dessiner dans un callback."""

    def __init__(self) -> None:
        """Charge les paramètres, ouvre l'écran et prépare l'état interne."""
        super().__init__('affichage_lcd')

        self.declare_parameter('peremption_alimentation_s', 3.0)
        self.declare_parameter('periode_rafraichissement_s', 0.1)
        self.declare_parameter('retroeclairage_pourcent', 80.0)

        self.peremption_alimentation_s = float(
            self.get_parameter('peremption_alimentation_s').value
        )
        self.periode_rafraichissement_s = float(
            self.get_parameter('periode_rafraichissement_s').value
        )
        retroeclairage_pourcent = float(
            self.get_parameter('retroeclairage_pourcent').value
        )

        self.ecran = EcranSt7789v()
        self.ecran.regler_retroeclairage(retroeclairage_pourcent)
        self.grille = GrilleTexte(self.ecran)

        # État interne, mis à jour uniquement par les callbacks ci-dessous.
        self.mode_conduite: str | None = None
        self.mode_conduite_precedent: str | None = None
        self.parole_en_cours = False
        self.page_courante = PAGE_TABLEAU_BORD
        self.etat_logique = EtatMesure()
        self.etat_moteur = EtatMesure()
        self.consigne_gauche = 0
        self.consigne_droite = 0

        # État de la transition d'ouverture de la bouche (0.0 à 1.0), mis à jour
        # uniquement par le timer d'affichage (_mettre_a_jour_ouverture_bouche),
        # jamais par une callback directe. Transition déjà "terminée" au départ,
        # pour déclencher un premier tirage dès que la parole commence.
        maintenant = self.get_clock().now()
        self._ouverture_bouche = 0.0
        self._depart_ouverture_bouche = 0.0
        self._cible_ouverture_bouche = 0.0
        self._depart_transition_bouche = maintenant
        self._duree_transition_bouche_s = 0.001
        self._fin_transition_bouche = maintenant

        # Dernière page effectivement dessinée à l'écran. None = inconnue : force
        # une resynchronisation complète au premier passage du timer, exactement
        # comme le premier effacer() attendu par GrilleTexte avant son premier
        # rendre().
        self._derniere_page_dessinee: int | None = None
        self._derniere_ouverture_dessinee: float | None = None

        qos_parole_en_cours = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            String, '/robot/mode_conduite', self._mode_conduite_callback, 10
        )
        self.create_subscription(
            Bool,
            '/robot/parole_en_cours',
            self._parole_en_cours_callback,
            qos_parole_en_cours,
        )
        self.create_subscription(
            Empty, '/affichage/page_suivante', self._page_suivante_callback, 10
        )
        self.create_subscription(
            BatteryState,
            '/alimentation/logique',
            self._alimentation_logique_callback,
            10,
        )
        self.create_subscription(
            BatteryState,
            '/alimentation/moteur',
            self._alimentation_moteur_callback,
            10,
        )
        self.create_subscription(
            ConsigneMoteurs,
            '/pico/commande_moteurs',
            self._commande_moteurs_callback,
            10,
        )

        self.minuterie = self.create_timer(
            self.periode_rafraichissement_s, self._rafraichir_callback
        )

        self.get_logger().info(
            'Affichage LCD initialisé : rafraîchissement toutes les '
            f'{self.periode_rafraichissement_s:.2f} s, '
            f'péremption alimentation {self.peremption_alimentation_s:.1f} s.'
        )

    # --- Callbacks des subscriptions ---

    def _mode_conduite_callback(self, msg: String) -> None:
        """Mémorise le mode reçu et force la page 0 sur un front manuel→autonomie."""
        nouveau_mode = msg.data

        # Front strict manuel -> autonomie seulement. Le tout premier message reçu
        # (mode_conduite_precedent encore None) n'est jamais un front.
        if (
            self.mode_conduite_precedent == 'manuel'
            and nouveau_mode == 'autonomie'
        ):
            self.page_courante = PAGE_BOUCHE

        self.mode_conduite_precedent = nouveau_mode
        self.mode_conduite = nouveau_mode

    def _parole_en_cours_callback(self, msg: Bool) -> None:
        """Mémorise si une annonce vocale est en cours."""
        self.parole_en_cours = msg.data

    def _page_suivante_callback(self, msg: Empty) -> None:
        """Bascule la page voulue, sauf pendant la parole où elle reste imposée."""
        if self.parole_en_cours:
            return
        self.page_courante = (self.page_courante + 1) % NB_PAGES

    def _alimentation_logique_callback(self, msg: BatteryState) -> None:
        """Mémorise tension et courant du rail logique."""
        self.etat_logique.tension_v = msg.voltage
        self.etat_logique.courant_a = msg.current
        self.etat_logique.horodatage_reception = self.get_clock().now()

    def _alimentation_moteur_callback(self, msg: BatteryState) -> None:
        """Mémorise tension et courant du rail moteur."""
        self.etat_moteur.tension_v = msg.voltage
        self.etat_moteur.courant_a = msg.current
        self.etat_moteur.horodatage_reception = self.get_clock().now()

    def _commande_moteurs_callback(self, msg: ConsigneMoteurs) -> None:
        """Mémorise la dernière consigne moteur réellement appliquée."""
        self.consigne_gauche = msg.gauche
        self.consigne_droite = msg.droite

    # --- Callbacks des timers ---

    def _rafraichir_callback(self) -> None:
        """Seul point de contact avec l'écran : décide et dessine la page active."""
        # La parole impose la page bouche, quelle que soit la page demandée.
        page_affichee = PAGE_BOUCHE if self.parole_en_cours else self.page_courante

        if page_affichee == PAGE_BOUCHE:
            self._mettre_a_jour_ouverture_bouche()
            self._dessiner_page_bouche()
        else:
            self._dessiner_page_tableau_bord()

    # --- Méthodes privées utilitaires ---

    def _sommets_rectangle_arrondi(
        self,
        centre_x: float,
        centre_y: float,
        demi_largeur: float,
        demi_hauteur: float,
    ) -> list[tuple[float, float]]:
        """
        Construit les sommets d'un rectangle à coins arrondis, net et symétrique.

        Rayon de coin uniforme (proportionnel à la demi-hauteur) ; les côtés droits
        ne portent aucun sommet, le polygone les relie implicitement d'un coin à
        l'autre.
        """
        gauche = centre_x - demi_largeur
        droite = centre_x + demi_largeur
        haut = centre_y - demi_hauteur
        bas = centre_y + demi_hauteur

        rayon = FACTEUR_RAYON_COIN_BOUCHE * demi_hauteur

        # Ordre horaire : haut-gauche, haut-droite, bas-droite, bas-gauche. Chaque
        # coin balaie un quart de cercle, du côté précédent vers le côté suivant.
        coins = (
            (gauche + rayon, haut + rayon, math.pi, 1.5 * math.pi),
            (droite - rayon, haut + rayon, 1.5 * math.pi, 2.0 * math.pi),
            (droite - rayon, bas - rayon, 0.0, 0.5 * math.pi),
            (gauche + rayon, bas - rayon, 0.5 * math.pi, math.pi),
        )

        sommets: list[tuple[float, float]] = []
        for centre_arc_x, centre_arc_y, angle_debut, angle_fin in coins:
            for indice_point in range(NB_POINTS_PAR_COIN_BOUCHE):
                fraction_coin = indice_point / (NB_POINTS_PAR_COIN_BOUCHE - 1)
                angle = angle_debut + (angle_fin - angle_debut) * fraction_coin
                sommets.append(
                    (
                        centre_arc_x + rayon * math.cos(angle),
                        centre_arc_y + rayon * math.sin(angle),
                    )
                )

        return sommets

    def _dessiner_image_bouche(self, ouverture: float) -> Image.Image:
        """Dessine l'image plein écran de la bouche pour une ouverture (0.0 à 1.0) donnée."""
        image = Image.new('RGB', (self.ecran.largeur, self.ecran.hauteur), NOIR)
        dessin = ImageDraw.Draw(image)

        demi_largeur_exterieur = DEMI_LARGEUR_EXTERIEUR_BOUCHE_MIN + (
            DEMI_LARGEUR_EXTERIEUR_BOUCHE_MAX - DEMI_LARGEUR_EXTERIEUR_BOUCHE_MIN
        ) * ouverture
        demi_hauteur_exterieur = DEMI_HAUTEUR_EXTERIEUR_BOUCHE_MIN + (
            DEMI_HAUTEUR_EXTERIEUR_BOUCHE_MAX - DEMI_HAUTEUR_EXTERIEUR_BOUCHE_MIN
        ) * ouverture
        sommets_exterieur = self._sommets_rectangle_arrondi(
            CENTRE_BOUCHE_X, CENTRE_BOUCHE_Y, demi_largeur_exterieur, demi_hauteur_exterieur
        )
        dessin.polygon(sommets_exterieur, fill=COULEUR_EXTERIEUR_BOUCHE)

        # Rectangle intérieur toujours visible, jamais absent : mince au repos,
        # il grandit surtout en hauteur avec l'ouverture.
        demi_largeur_interieur = demi_largeur_exterieur - MARGE_INTERIEUR_BOUCHE
        demi_hauteur_interieur = DEMI_HAUTEUR_INTERIEUR_BOUCHE_MIN + (
            DEMI_HAUTEUR_INTERIEUR_BOUCHE_MAX - DEMI_HAUTEUR_INTERIEUR_BOUCHE_MIN
        ) * ouverture
        sommets_interieur = self._sommets_rectangle_arrondi(
            CENTRE_BOUCHE_X, CENTRE_BOUCHE_Y, demi_largeur_interieur, demi_hauteur_interieur
        )
        dessin.polygon(sommets_interieur, fill=COULEUR_INTERIEUR_BOUCHE)

        return image

    def _ouverture_bouche_a(self, instant: Time) -> float:
        """Retourne l'ouverture lissée (smoothstep) à l'instant donné."""
        if instant >= self._fin_transition_bouche:
            return self._cible_ouverture_bouche

        ecoulement_s = (instant - self._depart_transition_bouche).nanoseconds / 1e9
        t = ecoulement_s / self._duree_transition_bouche_s
        lissage = 3.0 * t * t - 2.0 * t * t * t
        return (
            self._depart_ouverture_bouche
            + (self._cible_ouverture_bouche - self._depart_ouverture_bouche) * lissage
        )

    def _demarrer_transition_bouche(
        self,
        instant_depart: Time,
        ouverture_depart: float,
        ouverture_cible: float,
        duree_s: float,
    ) -> None:
        """Amorce une transition d'ouverture, en continuité depuis l'ouverture actuelle."""
        self._depart_transition_bouche = instant_depart
        self._depart_ouverture_bouche = ouverture_depart
        self._cible_ouverture_bouche = ouverture_cible
        self._duree_transition_bouche_s = duree_s
        self._fin_transition_bouche = instant_depart + Duration(seconds=duree_s)

    def _mettre_a_jour_ouverture_bouche(self) -> None:
        """Fait évoluer l'ouverture de la bouche, en continu et à un rythme irrégulier."""
        maintenant = self.get_clock().now()
        ouverture_courante = self._ouverture_bouche_a(maintenant)

        if not self.parole_en_cours:
            # Retour immédiat au repos, sans attendre la fin de la transition en
            # cours ; ne redémarre pas une transition déjà en cours vers 0.0.
            if self._cible_ouverture_bouche != 0.0:
                self._demarrer_transition_bouche(
                    maintenant, ouverture_courante, 0.0, DUREE_TRANSITION_ARRET_S
                )
        elif maintenant >= self._fin_transition_bouche:
            # Rythme irrégulier plutôt qu'un cycle mécanique entre paliers fixes,
            # avec une courte pause occasionnelle pour évoquer une respiration.
            if random.random() < PROBABILITE_PAUSE_RESPIRATION:
                cible = 0.0
                duree_s = random.uniform(*PLAGE_DUREE_PAUSE_RESPIRATION_S)
            else:
                cible = random.uniform(*PLAGE_CIBLE_OUVERTURE_BOUCHE)
                duree_s = random.uniform(*PLAGE_DUREE_TIRAGE_S)
            self._demarrer_transition_bouche(maintenant, ouverture_courante, cible, duree_s)

        self._ouverture_bouche = self._ouverture_bouche_a(maintenant)

    def _dessiner_page_bouche(self) -> None:
        """Affiche la bouche, seulement si l'ouverture a changé depuis le dernier tick."""
        if (
            self._derniere_page_dessinee == PAGE_BOUCHE
            and self._derniere_ouverture_dessinee == self._ouverture_bouche
        ):
            return
        image = self._dessiner_image_bouche(self._ouverture_bouche)
        self.ecran.afficher_image_pleine(image)
        self._derniere_page_dessinee = PAGE_BOUCHE
        self._derniere_ouverture_dessinee = self._ouverture_bouche

    def _dessiner_page_tableau_bord(self) -> None:
        """Dessine le tableau de bord : mode, alimentation, consignes moteur."""
        # La page bouche dessine directement sur l'écran, hors de GrilleTexte :
        # celle-ci ignore ce changement. Un effacer() resynchronise les deux états
        # avant de reprendre le rendu différentiel.
        if self._derniere_page_dessinee != PAGE_TABLEAU_BORD:
            self.grille.effacer(NOIR)
            self._derniere_page_dessinee = PAGE_TABLEAU_BORD

        separateur = '-' * self.grille.colonnes

        mode_texte = (self.mode_conduite or TEXTE_INCONNU).upper()
        self.grille.ecrire_texte(0, 0, f'MODE : {mode_texte}', CYAN)
        self.grille.ecrire_texte(0, 1, separateur, GRIS)

        self.grille.ecrire_texte(
            0, 2, self._texte_ligne_alimentation('Logique', self.etat_logique), VERT
        )
        self.grille.ecrire_texte(
            0, 3, self._texte_ligne_alimentation('Moteur', self.etat_moteur), VERT
        )
        self.grille.ecrire_texte(0, 4, separateur, GRIS)

        self.grille.ecrire_texte(
            0, 5, self._texte_ligne_moteur('Gauche', self.consigne_gauche), JAUNE
        )
        self.grille.ecrire_texte(
            0, 6, self._texte_ligne_moteur('Droite', self.consigne_droite), JAUNE
        )

        self.grille.rendre()

    def _texte_ligne_alimentation(self, etiquette: str, etat: EtatMesure) -> str:
        """Construit le texte d'une ligne tension/courant, '--' si périmée."""
        if self._est_perime(etat.horodatage_reception):
            valeurs = f'{TEXTE_INCONNU:>4} V {TEXTE_INCONNU:>5} A'
        else:
            # Le courant sert ici de repère de charge, jamais de signe de décharge :
            # la valeur absolue évite une lecture négative inutile à l'écran.
            valeurs = f'{etat.tension_v:>4.1f} V {abs(etat.courant_a):>5.1f} A'
        return f'{etiquette:<9}: {valeurs}'

    def _texte_ligne_moteur(self, etiquette: str, consigne: int) -> str:
        """Construit le texte d'une ligne de consigne moteur : sens et intensité PWM."""
        if consigne > 0:
            sens = 'avance'
        elif consigne < 0:
            sens = 'recule'
        else:
            sens = 'arrêt'
        return f'{etiquette:<9}: {sens:<7}{abs(consigne):>5}'

    def _est_perime(self, horodatage_reception: Time | None) -> bool:
        """Indique si une mesure n'a pas été reçue depuis plus que la péremption."""
        if horodatage_reception is None:
            return True
        ecart_s = (self.get_clock().now() - horodatage_reception).nanoseconds / 1e9
        return ecart_s > self.peremption_alimentation_s

    # --- Cycle de vie du nœud ---

    def fermer(self) -> None:
        """Libère l'écran (SPI et GPIO)."""
        self.ecran.fermer()


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2 puis exécute le nœud jusqu'à son arrêt."""
    rclpy.init(args=args)
    noeud: AffichageLcd | None = None

    try:
        noeud = AffichageLcd()
        rclpy.spin(noeud)
    except KeyboardInterrupt:
        pass
    finally:
        if noeud is not None:
            noeud.fermer()
            noeud.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
