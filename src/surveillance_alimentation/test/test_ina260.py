# -*- coding: utf-8 -*-
"""Tests du pilote INA260 avec un faux bus I2C, sans matériel ni `smbus2`."""

from surveillance_alimentation.ina260 import LecteurINA260


class FauxBusI2C:
    """Faux bus I2C minimal, qui retourne des octets fixes à toute lecture."""

    def __init__(self, octets: list[int]) -> None:
        """Retient les octets à retourner par `read_i2c_block_data`."""
        self.octets = octets

    def read_i2c_block_data(self, adresse: int, registre: int, longueur: int) -> list[int]:
        """Retourne les octets fixes, quels que soient l'adresse et le registre."""
        return self.octets


def test_lire_courant_a_convertit_le_complement_a_deux_negatif():
    """
    Les octets 0xFF, 0x38 doivent donner -0,25 A.

    Valeur calculée à la main : 0xFF38 = 65336 ; au-delà de 0x7FFF, on soustrait
    0x10000, soit 65336 - 65536 = -200 ; -200 x 0,00125 A (LSB courant) = -0,25 A.
    """
    bus = FauxBusI2C([0xFF, 0x38])
    lecteur = LecteurINA260(bus, adresse=0x40)

    assert lecteur.lire_courant_a() == -0.25
