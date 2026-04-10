# -*- coding: utf-8 -*-
"""Transport série minimal entre le Raspberry Pi 4 et le Raspberry Pi Pico WH."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import serial

VALEUR_MOTEUR_MIN: Final[int] = -1000
VALEUR_MOTEUR_MAX: Final[int] = 1000


@dataclass(slots=True)
class ConfigurationUART:
    """Regroupe les paramètres indispensables de la liaison UART."""

    port: str = "/dev/ttyS0"
    debit: int = 115200
    timeout_lecture: float = 0.1


class TransportSeriePico:
    """Gère uniquement l'ouverture du port et l'échange de lignes texte."""

    def __init__(self, configuration: ConfigurationUART | None = None) -> None:
        self.configuration = configuration or ConfigurationUART()
        self.serial: serial.Serial | None = None

    def connecter(self) -> None:
        """Ouvre la liaison série si elle n'est pas déjà disponible."""
        if self.serial is not None and self.serial.is_open:
            return

        self.serial = serial.Serial(
            port=self.configuration.port,
            baudrate=self.configuration.debit,
            timeout=self.configuration.timeout_lecture,
        )

    def fermer(self) -> None:
        """Ferme proprement le port série s'il est encore ouvert."""
        if self.serial is not None and self.serial.is_open:
            self.serial.close()
        self.serial = None

    def envoyer_commande(self, commande: str) -> None:
        """Envoie une commande ASCII terminée par un saut de ligne."""
        self.connecter()
        ligne = f"{commande}\n".encode("ascii")
        assert self.serial is not None
        self.serial.write(ligne)
        self.serial.flush()

    def lire_ligne(self) -> str | None:
        """Lit une ligne complète si le Pico a répondu, sinon retourne `None`."""
        self.connecter()
        assert self.serial is not None
        donnees = self.serial.readline()
        if not donnees:
            return None
        return donnees.decode("ascii", errors="replace").strip()

    def ping(self) -> None:
        """Demande au Pico de répondre pour tester la liaison logique."""
        self.envoyer_commande("PING")

    def stop(self) -> None:
        """Demande l'arrêt immédiat des moteurs."""
        self.envoyer_commande("STOP")

    def demander_status(self) -> None:
        """Demande un état texte simple au Pico."""
        self.envoyer_commande("STATUS")

    def set_moteurs(self, gauche: int, droite: int) -> None:
        """Envoie une consigne moteur brute gauche/droite."""
        if not VALEUR_MOTEUR_MIN <= gauche <= VALEUR_MOTEUR_MAX:
            raise ValueError("gauche hors plage -1000..1000")
        if not VALEUR_MOTEUR_MIN <= droite <= VALEUR_MOTEUR_MAX:
            raise ValueError("droite hors plage -1000..1000")
        self.envoyer_commande(f"SET {gauche} {droite}")
