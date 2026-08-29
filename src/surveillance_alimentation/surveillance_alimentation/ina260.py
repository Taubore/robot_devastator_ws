# -*- coding: utf-8 -*-
"""
Pilote minimal du capteur de tension et courant Adafruit INA260 sur bus I2C.

Ce module ne connaît que le protocole du circuit : il ne dépend d'aucun élément
propre à un robot. Le numéro de bus, l'adresse et les seuils sont fournis par
l'appelant, jamais codés ici.

Registres, facteurs de conversion et ordre des octets vérifiés contre le
datasheet officiel :

    Texas Instruments, « INA260 Precision Current and Power Monitor With
    Low-Drift, Precision Integrated Shunt », SBOS656C, révisé décembre 2016.

- Table 4 (Register Set Summary) : 00h Configuration, 01h Current, 02h Bus
  Voltage, 03h Power, FEh Manufacturer ID (0x5449), FFh Die ID (0x2270).
- Section 8.6.2 (Current Register) : LSB fixe 1,25 mA ; valeur codée en
  complément à deux sur 16 bits (bit 15 CSIGN) pour représenter les courants
  négatifs.
- Section 8.6.3 (Bus Voltage Register) : LSB fixe 1,25 mV ; toujours positif
  (bit 15 forcé à zéro) ; pleine échelle 40,96 V.
- Section 8.5.3.2 et Figures 25-26 : les mots de 16 bits circulent octet de
  poids fort en premier (big-endian).
- Section 8.6.1 et Table 5 : configuration au démarrage 0x6127 (mesure continue
  tension bus + shunt, conversion 1,1 ms, moyennage désactivé). Les bits 14-12
  sont réservés et conservés tels quels ; ce pilote n'ajuste que le champ de
  moyennage (bits 11-9, AVG).
"""

from __future__ import annotations

from typing import Final

from smbus2 import SMBus

# --- Cartographie des registres (datasheet SBOS656C, Table 4) ---
REG_CONFIGURATION: Final[int] = 0x00
REG_COURANT: Final[int] = 0x01
REG_TENSION_BUS: Final[int] = 0x02
REG_ID_FABRICANT: Final[int] = 0xFE
REG_ID_PUCE: Final[int] = 0xFF

# Valeurs d'identification figées du circuit (datasheet Table 4).
ID_FABRICANT_TI: Final[int] = 0x5449
ID_PUCE_INA260: Final[int] = 0x2270

# LSB fixes du INA260 (datasheet sections 8.6.2 et 8.6.3), en unités SI.
LSB_COURANT_A: Final[float] = 0.00125
LSB_TENSION_BUS_V: Final[float] = 0.00125

# Configuration au démarrage (datasheet section 8.6.1 / Table 5) : mesure
# continue tension bus + shunt. Seul le champ AVG (bits 11-9) est modifié ici.
CONFIGURATION_PAR_DEFAUT: Final[int] = 0x6127
_MASQUE_MOYENNAGE: Final[int] = 0b111 << 9

# Codes du champ AVG (datasheet Table 5) : nombre d'échantillons moyennés -> code.
CODES_MOYENNAGE: Final[dict[int, int]] = {
    1: 0b000,
    4: 0b001,
    16: 0b010,
    64: 0b011,
    128: 0b100,
    256: 0b101,
    512: 0b110,
    1024: 0b111,
}

# Conversion complément à deux sur 16 bits pour le registre de courant.
_PLAGE_16_BITS: Final[int] = 1 << 16
_SEUIL_SIGNE_16_BITS: Final[int] = 1 << 15

_NB_OCTETS_MOT: Final[int] = 2


class LecteurINA260:
    """
    Lit la tension et le courant d'un INA260 unique à une adresse I2C donnée.

    L'objet ne possède pas le bus : il reçoit un `SMBus` déjà ouvert, partagé
    entre tous les capteurs de la même ligne I2C. Les erreurs de transmission
    (`OSError`) ne sont pas interceptées ici : elles remontent à l'appelant, qui
    choisit la stratégie de dégradation.
    """

    def __init__(self, bus: SMBus, adresse: int) -> None:
        """Retient le bus partagé et l'adresse I2C du capteur."""
        self.bus = bus
        self.adresse = adresse

    # --- Méthodes publiques ---

    def verifier_identite(self) -> None:
        """
        Vérifie qu'un INA260 répond bien à l'adresse configurée.

        Lève `RuntimeError` si les registres d'identification ne correspondent
        pas aux valeurs figées du datasheet : cela révèle une mauvaise adresse
        dans le YAML ou un autre circuit à cette adresse.
        """
        id_fabricant = self._lire_mot(REG_ID_FABRICANT)
        id_puce = self._lire_mot(REG_ID_PUCE)

        if id_fabricant != ID_FABRICANT_TI or id_puce != ID_PUCE_INA260:
            raise RuntimeError(
                f"Le circuit à l'adresse 0x{self.adresse:02X} ne s'identifie pas "
                f'comme un INA260 (fabricant lu 0x{id_fabricant:04X}, '
                f'puce lue 0x{id_puce:04X}).'
            )

    def configurer_moyennage(self, nb_echantillons: int) -> None:
        """
        Programme le moyennage matériel pour lisser les lectures à basse cadence.

        `nb_echantillons` doit valoir une des tailles du champ AVG du datasheet
        (1, 4, 16, 64, 128, 256, 512, 1024). Les autres bits de configuration
        gardent leur valeur de démarrage.
        """
        if nb_echantillons not in CODES_MOYENNAGE:
            raise ValueError(
                f'Taille de moyennage invalide : {nb_echantillons}. '
                f'Valeurs permises : {sorted(CODES_MOYENNAGE)}.'
            )

        code = CODES_MOYENNAGE[nb_echantillons]
        configuration = (CONFIGURATION_PAR_DEFAUT & ~_MASQUE_MOYENNAGE) | (code << 9)
        self._ecrire_mot(REG_CONFIGURATION, configuration)

    def lire_tension_v(self) -> float:
        """Retourne la tension du bus en volts, toujours positive."""
        return self._lire_mot(REG_TENSION_BUS) * LSB_TENSION_BUS_V

    def lire_courant_a(self) -> float:
        """
        Retourne le courant en ampères, signe compris.

        Le registre est codé en complément à deux sur 16 bits : une valeur au
        delà de 0x7FFF représente un courant négatif (datasheet section 8.6.2).
        Le sens physique du signe dépend du câblage IN+/IN- du capteur.
        """
        brut = self._lire_mot(REG_COURANT)
        if brut >= _SEUIL_SIGNE_16_BITS:
            brut -= _PLAGE_16_BITS
        return brut * LSB_COURANT_A

    # --- Méthodes privées utilitaires ---

    def _lire_mot(self, registre: int) -> int:
        """Lit un registre 16 bits et recompose l'ordre big-endian du circuit."""
        octets = self.bus.read_i2c_block_data(self.adresse, registre, _NB_OCTETS_MOT)
        return (octets[0] << 8) | octets[1]

    def _ecrire_mot(self, registre: int, valeur: int) -> None:
        """Écrit un registre 16 bits en respectant l'ordre big-endian du circuit."""
        octet_fort = (valeur >> 8) & 0xFF
        octet_faible = valeur & 0xFF
        self.bus.write_i2c_block_data(self.adresse, registre, [octet_fort, octet_faible])
