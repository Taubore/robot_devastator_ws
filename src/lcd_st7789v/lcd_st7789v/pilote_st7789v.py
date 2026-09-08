# -*- coding: utf-8 -*-
"""
Pilote bas niveau de l'écran LCD Waveshare 2 pouces (contrôleur ST7789V, 240x320,
RGB565, SPI, écriture seule).

Ce module ne dépend d'aucun élément propre à un robot ni à ROS 2 : il reçoit ses
broches et son bus SPI en paramètres et ne connaît que le protocole du contrôleur.
Aucune fonction de dessin n'y est offerte (pas de texte, de ligne, de forme ni de
couleur) : Pillow s'en charge dans les couches appelantes ; ce pilote se contente de
transmettre une image déjà construite.

Bibliothèques utilisées : `spidev` pour le bus SPI, `lgpio` pour les broches DC,
RST et BL (y compris le PWM logiciel du rétroéclairage), `numpy` et Pillow pour la
conversion d'image. `lgpio` est la seule bibliothèque d'accès GPIO autorisée dans ce
projet (voir AGENTS.md, section GPIO et SPI) : y mélanger `gpiozero`, `RPi.GPIO`,
`pigpio`, `bcm2835` ou `wiringPi` provoquerait des conflits d'accès aux broches.

La séquence d'initialisation du contrôleur (réglages gamma compris), les codes de
commande, la logique de définition de la fenêtre d'adressage, la formule de
conversion RGB565 et la séquence de réinitialisation matérielle sont repris tels
quels du code de démonstration Waveshare (dépôt `LCD_Module_RPI_code`, licence MIT,
Copyright 2022 Waveshare Electronics) : ce sont des faits matériels du contrôleur et
du panneau, déjà validés sur le robot physique, pas du code à reformuler. La
structure de classe, la gestion des ressources, les identifiants et l'interface
publique sont propres à ce projet.
"""

from __future__ import annotations

import time
from typing import Final

import lgpio
import numpy as np
import spidev
from PIL import Image

# --- Codes de commande du contrôleur ST7789V utilisés par ce pilote ---
_CMD_MADCTL: Final[int] = 0x36        # Contrôle d'accès mémoire (orientation, ordre RVB)
_CMD_COLMOD: Final[int] = 0x3A        # Format de pixel de l'interface
_CMD_INVOFF: Final[int] = 0x21        # Inversion des couleurs (requise par ce panneau)
_CMD_CASET: Final[int] = 0x2A         # Column address set
_CMD_RASET: Final[int] = 0x2B         # Row address set
_CMD_RAMWR: Final[int] = 0x2C         # Memory write
_CMD_PORCTRL: Final[int] = 0xB2       # Porch setting
_CMD_GCTRL: Final[int] = 0xB7         # Gate control
_CMD_VCOMS: Final[int] = 0xBB         # VCOM setting
_CMD_LCMCTRL: Final[int] = 0xC0       # LCM control
_CMD_VDVVRHEN: Final[int] = 0xC2      # VDV et VRH command enable
_CMD_VRHS: Final[int] = 0xC3          # VRH set
_CMD_VDVS: Final[int] = 0xC4          # VDV set
_CMD_FRCTRL2: Final[int] = 0xC6       # Frame rate control
_CMD_PWCTRL1: Final[int] = 0xD0       # Power control 1
_CMD_PVGAMCTRL: Final[int] = 0xE0     # Réglages gamma positifs
_CMD_NVGAMCTRL: Final[int] = 0xE1     # Réglages gamma négatifs
_CMD_SLPOUT: Final[int] = 0x11        # Sortie du mode veille
_CMD_DISPON: Final[int] = 0x29        # Allumage de l'affichage

# Orientation logique : MADCTL réglé une seule fois à l'initialisation, jamais
# recalculé par image. Valeurs reprises telles quelles du code Waveshare.
_MADCTL_PORTRAIT: Final[int] = 0x00   # Orientation native du panneau (240 x 320)
_MADCTL_PAYSAGE: Final[int] = 0x70    # Rotation 90 degrés (320 x 240)

# Limite habituelle d'un transfert spidev sur Raspberry Pi sans reconfiguration du
# tampon noyau (voir contrainte de conception « découpage des transferts SPI »).
_TAILLE_BLOC_SPI_DEFAUT: Final[int] = 4096


class EcranSt7789v:
    """
    Pilote bas niveau de l'écran Waveshare 2 pouces (contrôleur ST7789V).

    Écriture seule : aucune lecture du panneau n'est effectuée ni possible (MISO
    n'est pas câblé). Cette classe ne dessine rien ; elle transmet des images
    Pillow déjà construites par les couches supérieures.

    Gestionnaire de contexte : utiliser `with EcranSt7789v(...) as ecran:` pour
    garantir la libération des broches GPIO et du bus SPI même en cas d'exception,
    lgpio verrouillant les broches au niveau noyau.
    """

    LARGEUR_NATIVE: Final[int] = 240
    HAUTEUR_NATIVE: Final[int] = 320

    def __init__(
        self,
        bus_spi: int = 0,
        peripherique_spi: int = 0,
        broche_dc: int = 25,
        broche_rst: int = 24,
        broche_bl: int = 12,
        frequence_spi_hz: int = 8_000_000,
        frequence_pwm_bl_hz: int = 1000,
        paysage: bool = True,
        puce_gpio: int = 0,
        taille_bloc_spi: int = _TAILLE_BLOC_SPI_DEFAUT,
    ) -> None:
        """
        Ouvre le bus SPI, réclame les broches GPIO puis initialise le contrôleur.

        `frequence_spi_hz` : 8 MHz par défaut, valeur prudente. Pour l'augmenter,
        procéder par paliers (par exemple 8 -> 16 -> 24 MHz) jusqu'à l'apparition
        d'artefacts à l'écran, puis redescendre d'un palier.

        `paysage` fixe l'orientation logique pour toute la durée de vie de
        l'instance, selon le montage physique du panneau (côté long à l'horizontal
        si True, soit 320 x 240 ; False donne l'orientation native 240 x 320). Ce
        n'est pas une fonction de dessin : l'orientation ne change jamais entre
        deux appels d'affichage sur la même instance.

        Si l'initialisation échoue à mi-chemin (broche déjà retenue par un autre
        processus, bus SPI indisponible), les ressources déjà acquises sont
        libérées avant que l'exception ne remonte à l'appelant.
        """
        self._broche_dc = broche_dc
        self._broche_rst = broche_rst
        self._broche_bl = broche_bl
        self._frequence_pwm_bl_hz = frequence_pwm_bl_hz
        self._taille_bloc_spi = taille_bloc_spi

        if paysage:
            self.largeur, self.hauteur = self.HAUTEUR_NATIVE, self.LARGEUR_NATIVE
        else:
            self.largeur, self.hauteur = self.LARGEUR_NATIVE, self.HAUTEUR_NATIVE
        self._madctl = _MADCTL_PAYSAGE if paysage else _MADCTL_PORTRAIT

        self._poignee_gpio: int | None = None
        self._spi: spidev.SpiDev | None = None

        try:
            self._poignee_gpio = lgpio.gpiochip_open(puce_gpio)
            lgpio.gpio_claim_output(self._poignee_gpio, self._broche_dc, 0)
            lgpio.gpio_claim_output(self._poignee_gpio, self._broche_rst, 1)
            lgpio.gpio_claim_output(self._poignee_gpio, self._broche_bl, 0)
            # Retroéclairage éteint tant que l'écran n'est pas initialisé.
            lgpio.tx_pwm(self._poignee_gpio, self._broche_bl, self._frequence_pwm_bl_hz, 0)

            self._spi = spidev.SpiDev()
            self._spi.open(bus_spi, peripherique_spi)
            self._spi.max_speed_hz = frequence_spi_hz
            self._spi.mode = 0b00

            self._initialiser_controleur()
        except Exception:
            self.fermer()
            raise

    # --- Méthodes publiques ---

    def afficher_image_pleine(self, image: Image.Image) -> None:
        """
        Affiche une image Pillow en plein écran.

        L'image doit avoir exactement les dimensions effectives de l'écran selon
        l'orientation choisie à la construction (`self.largeur`, `self.hauteur`) ;
        une taille différente lève `ValueError` plutôt que d'afficher une image
        décalée ou tronquée.
        """
        if image.size != (self.largeur, self.hauteur):
            raise ValueError(
                f"Image de taille {image.size} incompatible avec l'écran plein "
                f'{(self.largeur, self.hauteur)}'
            )
        self._definir_fenetre(0, 0, self.largeur, self.hauteur)
        self._envoyer_image(image)

    def afficher_image_region(self, image: Image.Image, x: int, y: int) -> None:
        """
        Affiche une image Pillow dans un rectangle dont le coin supérieur gauche
        est (x, y) et dont la taille est celle de l'image reçue.

        Lève `ValueError` si la région déborde de l'écran : le pilote échoue
        bruyamment plutôt que d'afficher une image décalée.
        """
        largeur_region, hauteur_region = image.size
        x_fin = x + largeur_region
        y_fin = y + hauteur_region
        if x < 0 or y < 0 or x_fin > self.largeur or y_fin > self.hauteur:
            raise ValueError(
                f'Région ({x}, {y}) -> ({x_fin}, {y_fin}) hors des bornes de '
                f"l'écran {(self.largeur, self.hauteur)}"
            )
        self._definir_fenetre(x, y, x_fin, y_fin)
        self._envoyer_image(image)

    def regler_retroeclairage(self, intensite_pourcent: float) -> None:
        """
        Règle l'intensité du rétroéclairage par PWM logiciel, de 0 à 100.

        Le PWM est entièrement logiciel (`lgpio.tx_pwm`, cadencé par alertes) :
        GPIO12 n'est pas utilisée ici pour une capacité PWM matérielle, seulement
        parce qu'elle était libre sur ce robot (GPIO18 est réservée à l'interface
        I2S de la chaîne audio).
        """
        if not 0 <= intensite_pourcent <= 100:
            raise ValueError(f'Intensité hors bornes [0, 100] : {intensite_pourcent}')
        lgpio.tx_pwm(
            self._poignee_gpio, self._broche_bl, self._frequence_pwm_bl_hz, intensite_pourcent
        )

    # --- Méthodes privées utilitaires ---

    def _commande(self, valeur: int) -> None:
        """Envoie un octet de commande (broche DC à l'état bas)."""
        lgpio.gpio_write(self._poignee_gpio, self._broche_dc, 0)
        self._spi.writebytes2([valeur])

    def _donnee(self, valeur: int) -> None:
        """Envoie un octet de donnée associé à la dernière commande (DC à l'état haut)."""
        lgpio.gpio_write(self._poignee_gpio, self._broche_dc, 1)
        self._spi.writebytes2([valeur])

    def _reinitialiser_materiel(self) -> None:
        """
        Séquence de réinitialisation matérielle du contrôleur, reprise telle
        quelle du code Waveshare (impulsion et temporisations de 10 ms).
        """
        lgpio.gpio_write(self._poignee_gpio, self._broche_rst, 1)
        time.sleep(0.01)
        lgpio.gpio_write(self._poignee_gpio, self._broche_rst, 0)
        time.sleep(0.01)
        lgpio.gpio_write(self._poignee_gpio, self._broche_rst, 1)
        time.sleep(0.01)

    def _initialiser_controleur(self) -> None:
        """
        Séquence d'initialisation du ST7789V, reprise telle quelle du code de
        démonstration Waveshare (registres et réglages gamma compris). Seul
        l'octet de MADCTL diffère de la référence : il encode ici l'orientation
        choisie à la construction plutôt qu'une valeur fixe.
        """
        self._reinitialiser_materiel()

        self._commande(_CMD_MADCTL)
        self._donnee(self._madctl)

        self._commande(_CMD_COLMOD)
        self._donnee(0x05)

        self._commande(_CMD_INVOFF)

        self._commande(_CMD_PORCTRL)
        for valeur in (0x0C, 0x0C, 0x00, 0x33, 0x33):
            self._donnee(valeur)

        self._commande(_CMD_GCTRL)
        self._donnee(0x35)

        self._commande(_CMD_VCOMS)
        self._donnee(0x1F)

        self._commande(_CMD_LCMCTRL)
        self._donnee(0x2C)

        self._commande(_CMD_VDVVRHEN)
        self._donnee(0x01)

        self._commande(_CMD_VRHS)
        self._donnee(0x12)

        self._commande(_CMD_VDVS)
        self._donnee(0x20)

        self._commande(_CMD_FRCTRL2)
        self._donnee(0x0F)

        self._commande(_CMD_PWCTRL1)
        for valeur in (0xA4, 0xA1):
            self._donnee(valeur)

        self._commande(_CMD_PVGAMCTRL)
        for valeur in (
            0xD0, 0x08, 0x11, 0x08, 0x0C, 0x15, 0x39,
            0x33, 0x50, 0x36, 0x13, 0x14, 0x29, 0x2D,
        ):
            self._donnee(valeur)

        self._commande(_CMD_NVGAMCTRL)
        for valeur in (
            0xD0, 0x08, 0x10, 0x08, 0x06, 0x06, 0x39,
            0x44, 0x51, 0x0B, 0x16, 0x14, 0x2F, 0x31,
        ):
            self._donnee(valeur)

        self._commande(_CMD_INVOFF)
        self._commande(_CMD_SLPOUT)
        self._commande(_CMD_DISPON)

    def _definir_fenetre(self, x_debut: int, y_debut: int, x_fin: int, y_fin: int) -> None:
        """
        Définit la fenêtre d'adressage active du contrôleur.

        Reprend la logique Waveshare telle quelle, y compris la particularité de
        l'octet bas de fin de fenêtre transmis comme (fin - 1) alors que l'octet
        haut ne l'est pas : c'est le comportement exact du contrôleur, validé sur
        le panneau physique, pas une asymétrie à corriger.
        """
        self._commande(_CMD_CASET)
        self._donnee(x_debut >> 8)
        self._donnee(x_debut & 0xFF)
        self._donnee(x_fin >> 8)
        self._donnee((x_fin - 1) & 0xFF)

        self._commande(_CMD_RASET)
        self._donnee(y_debut >> 8)
        self._donnee(y_debut & 0xFF)
        self._donnee(y_fin >> 8)
        self._donnee((y_fin - 1) & 0xFF)

        self._commande(_CMD_RAMWR)

    def _envoyer_image(self, image: Image.Image) -> None:
        """
        Convertit une image Pillow en RGB565 et l'envoie par blocs sur le SPI.

        Formule de conversion reprise telle quelle du code Waveshare : l'octet
        haut porte les 5 bits de rouge et les 3 bits de poids fort du vert,
        l'octet bas porte les 3 bits de poids faible du vert et les 5 bits de
        bleu. Le découpage en blocs évite de dépasser la taille maximale d'un
        transfert spidev sur ce noyau.
        """
        tableau = np.asarray(image.convert('RGB'))
        pixels = np.zeros((tableau.shape[0], tableau.shape[1], 2), dtype=np.uint8)
        pixels[..., 0] = (tableau[..., 0] & 0xF8) | (tableau[..., 1] >> 5)
        pixels[..., 1] = ((tableau[..., 1] << 3) & 0xE0) | (tableau[..., 2] >> 3)
        octets = pixels.tobytes()

        lgpio.gpio_write(self._poignee_gpio, self._broche_dc, 1)
        for debut in range(0, len(octets), self._taille_bloc_spi):
            self._spi.writebytes2(octets[debut:debut + self._taille_bloc_spi])

    # --- Cycle de vie ---

    def fermer(self) -> None:
        """
        Libère le bus SPI et les broches GPIO.

        Appelée automatiquement par `__exit__`, mais aussi utilisable seule ou
        depuis un `finally`. Tolérante aux ressources partiellement acquises : une
        instance dont la construction a échoué à mi-chemin peut être fermée sans
        lever d'exception, pour ne jamais laisser une broche retenue au niveau
        noyau après une sortie anormale.
        """
        if self._poignee_gpio is not None:
            try:
                lgpio.tx_pwm(self._poignee_gpio, self._broche_bl, self._frequence_pwm_bl_hz, 0)
            except Exception:
                pass
            for broche in (self._broche_dc, self._broche_rst, self._broche_bl):
                try:
                    lgpio.gpio_free(self._poignee_gpio, broche)
                except Exception:
                    pass
            try:
                lgpio.gpiochip_close(self._poignee_gpio)
            except Exception:
                pass
            self._poignee_gpio = None

        if self._spi is not None:
            self._spi.close()
            self._spi = None

    def __enter__(self) -> 'EcranSt7789v':
        return self

    def __exit__(self, type_exc, exc, trace) -> None:
        self.fermer()
