# -*- coding: utf-8 -*-
"""Tests de la logique pure d'évaluation des seuils d'alerte, sans ROS 2 ni I2C."""

from surveillance_alimentation.logique_alerte import (
    ConfigurationAlerte,
    evaluer_seuils,
    SeuilAlerte,
)

PAS_S = 1.0


def _configuration() -> ConfigurationAlerte:
    """Retourne une configuration d'alerte type pour les tests."""
    return ConfigurationAlerte(
        courant_max_evaluation_a=1.0,
        temporisation_s=5.0,
        hysteresis_rearmement_v=0.15,
    )


def _seuil() -> SeuilAlerte:
    """Retourne un seuil unique désarmé, prêt à être évalué."""
    return SeuilAlerte(nom='avertissement', tension_v=11.0, evenement='batterie_faible')


def test_conduite_hachee_finit_par_armer_le_seuil():
    """
    Une conduite hachée finit par armer le seuil malgré des coupures de courant.

    Alterne des cycles à courant élevé (porte fermée, condition inconnue) et des
    cycles à courant faible sous le seuil (condition vraie). L'accumulateur ne
    doit jamais être remis à zéro par les cycles à courant élevé : seul un cycle
    à tension au-dessus du seuil et à courant faible le ferait.
    """
    configuration = _configuration()
    seuil = _seuil()

    cycles = [
        (10.5, 2.0),  # courant élevé : porte fermée, inconnue.
        (10.5, 0.5),  # courant faible, tension basse : condition vraie (1 s).
        (10.5, 2.0),  # courant élevé : porte fermée, inconnue.
        (10.5, 0.5),  # courant faible, tension basse : condition vraie (2 s).
        (10.5, 2.0),  # courant élevé : porte fermée, inconnue.
        (10.5, 0.5),  # courant faible, tension basse : condition vraie (3 s).
        (10.5, 2.0),  # courant élevé : porte fermée, inconnue.
        (10.5, 0.5),  # courant faible, tension basse : condition vraie (4 s).
        (10.5, 2.0),  # courant élevé : porte fermée, inconnue.
        (10.5, 0.5),  # courant faible, tension basse : condition vraie (5 s => armement).
    ]

    resultats_armement = []
    for tension_v, courant_a in cycles:
        resultats = evaluer_seuils([seuil], configuration, tension_v, courant_a, PAS_S)
        resultats_armement.extend(r for r in resultats if r.genre == 'armement')

    assert seuil.arme
    assert len(resultats_armement) == 1
    assert resultats_armement[0].evenement == 'batterie_faible'


def test_porte_de_courant_fermee_en_permanence_narme_jamais():
    """Un courant toujours au-dessus du seuil d'évaluation n'arme jamais le seuil."""
    configuration = _configuration()
    seuil = _seuil()

    for _ in range(20):
        resultats = evaluer_seuils([seuil], configuration, 9.0, 5.0, PAS_S)
        assert resultats == []

    assert not seuil.arme
    assert seuil.duree_condition_s == 0.0


def test_desarmement_par_hysteresis_reinitialise_le_rappel():
    """
    Le désarmement exige l'hystérésis complète et réinitialise le compteur de rappel.

    Une fois armé, le seuil ne se désarme pas tant que la tension ne dépasse pas
    `seuil + hysteresis_rearmement_v`. Le désarmement doit remettre à zéro le
    compteur de rappel (`duree_depuis_rappel_s`), pour qu'un futur réarmement
    reparte proprement.
    """
    configuration = _configuration()
    seuil = SeuilAlerte(
        nom='avertissement',
        tension_v=11.0,
        evenement='batterie_faible',
        periode_rappel_s=10.0,
    )

    # Armement après temporisation.
    for _ in range(5):
        evaluer_seuils([seuil], configuration, 10.5, 0.5, PAS_S)
    assert seuil.arme

    # Fait avancer le compteur de rappel avant de tenter le désarmement.
    evaluer_seuils([seuil], configuration, 10.5, 0.5, PAS_S)
    assert seuil.duree_depuis_rappel_s > 0.0

    # Tension remontée mais sous le seuil d'hystérésis (11.0 + 0.15) : pas de
    # désarmement.
    resultats = evaluer_seuils([seuil], configuration, 11.05, 0.5, PAS_S)
    assert seuil.arme
    assert not any(r.genre == 'retablissement' for r in resultats)

    # Tension au-dessus du seuil d'hystérésis : désarmement.
    resultats = evaluer_seuils([seuil], configuration, 11.20, 0.5, PAS_S)
    assert not seuil.arme
    assert seuil.duree_depuis_rappel_s == 0.0
    assert any(r.genre == 'retablissement' for r in resultats)
