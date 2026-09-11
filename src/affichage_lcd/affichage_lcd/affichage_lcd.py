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
from typing import Final

from commun.msg import ConsigneMoteurs
from lcd_st7789v.pilote_st7789v import EcranSt7789v
from lcd_st7789v.rendu_texte import CYAN, GrilleTexte, JAUNE, NOIR, VERT
from PIL import Image, ImageDraw
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.time import Time
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, Empty, String

NB_PAGES: Final[int] = 2
PAGE_BOUCHE: Final[int] = 0
PAGE_TABLEAU_BORD: Final[int] = 1

TEXTE_INCONNU: Final[str] = '--'


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
        self.image_bouche = self._construire_image_bouche()

        # État interne, mis à jour uniquement par les callbacks ci-dessous.
        self.mode_conduite: str | None = None
        self.mode_conduite_precedent: str | None = None
        self.parole_en_cours = False
        self.page_courante = PAGE_TABLEAU_BORD
        self.etat_logique = EtatMesure()
        self.etat_moteur = EtatMesure()
        self.consigne_gauche = 0
        self.consigne_droite = 0

        # Dernière page effectivement dessinée à l'écran. None = inconnue : force
        # une resynchronisation complète au premier passage du timer, exactement
        # comme le premier effacer() attendu par GrilleTexte avant son premier
        # rendre().
        self._derniere_page_dessinee: int | None = None

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
            self._dessiner_page_bouche()
        else:
            self._dessiner_page_tableau_bord()

    # --- Méthodes privées utilitaires ---

    def _construire_image_bouche(self) -> Image.Image:
        """Construit une fois l'image plein écran de la bouche simple (Pillow)."""
        image = Image.new('RGB', (self.ecran.largeur, self.ecran.hauteur), NOIR)
        dessin = ImageDraw.Draw(image)

        centre_x, centre_y = self.ecran.largeur // 2, self.ecran.hauteur // 2
        demi_largeur, demi_hauteur = 60, 25
        dessin.ellipse(
            (
                centre_x - demi_largeur,
                centre_y - demi_hauteur,
                centre_x + demi_largeur,
                centre_y + demi_hauteur,
            ),
            fill=(255, 255, 255),
        )
        return image

    def _dessiner_page_bouche(self) -> None:
        """Affiche la bouche, seulement si elle n'était pas déjà à l'écran."""
        if self._derniere_page_dessinee == PAGE_BOUCHE:
            return
        self.ecran.afficher_image_pleine(self.image_bouche)
        self._derniere_page_dessinee = PAGE_BOUCHE

    def _dessiner_page_tableau_bord(self) -> None:
        """Dessine le tableau de bord : mode, alimentation, consignes moteur."""
        # La page bouche dessine directement sur l'écran, hors de GrilleTexte :
        # celle-ci ignore ce changement. Un effacer() resynchronise les deux états
        # avant de reprendre le rendu différentiel.
        if self._derniere_page_dessinee != PAGE_TABLEAU_BORD:
            self.grille.effacer(NOIR)
            self._derniere_page_dessinee = PAGE_TABLEAU_BORD

        mode_texte = (self.mode_conduite or TEXTE_INCONNU).upper()
        self.grille.ecrire_texte(0, 0, f'Mode: {mode_texte:<10}', CYAN)

        self.grille.ecrire_texte(
            0, 2, self._texte_ligne_alimentation('Log', self.etat_logique), VERT
        )
        self.grille.ecrire_texte(
            0, 3, self._texte_ligne_alimentation('Mot', self.etat_moteur), VERT
        )

        self.grille.ecrire_texte(
            0, 5, self._texte_ligne_moteur('G', self.consigne_gauche), JAUNE
        )
        self.grille.ecrire_texte(
            0, 6, self._texte_ligne_moteur('D', self.consigne_droite), JAUNE
        )

        self.grille.rendre()

    def _texte_ligne_alimentation(self, prefixe: str, etat: EtatMesure) -> str:
        """Construit le texte d'une ligne tension/courant, '--' si périmée."""
        if self._est_perime(etat.horodatage_reception):
            return f'{prefixe} {TEXTE_INCONNU:>5} V {TEXTE_INCONNU:>6} A'
        return f'{prefixe} {etat.tension_v:>5.1f} V {etat.courant_a:>6.2f} A'

    def _texte_ligne_moteur(self, prefixe: str, consigne: int) -> str:
        """Construit le texte d'une ligne de consigne moteur : sens et intensité PWM."""
        if consigne > 0:
            sens = 'avance'
        elif consigne < 0:
            sens = 'recule'
        else:
            sens = 'arrêt'
        return f'{prefixe} {sens:<6} {abs(consigne):>4}'

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
