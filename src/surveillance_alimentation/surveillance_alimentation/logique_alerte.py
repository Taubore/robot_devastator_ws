# -*- coding: utf-8 -*-
"""
Logique pure d'évaluation des seuils d'alerte d'un rail d'alimentation.

Ce module ne dépend ni de `rclpy` ni de `smbus2` et ne journalise rien : il reçoit
des nombres (seuils, configuration, mesures) et retourne une liste de résultats.
L'appelant (le nœud ROS 2) décide seul quoi journaliser et quoi publier. Cette
séparation rend la logique testable sans matériel ni contexte ROS 2.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SeuilAlerte:
    """
    Décrit un niveau d'alerte d'un rail et retient son état d'armement.

    Un seuil dont la tension est nulle ou négative est considéré désactivé : il
    n'est jamais évalué. Cela permet de n'activer qu'un seul niveau si besoin.

    La temporisation d'armement est suivie par un accumulateur de durée
    (`duree_condition_s`) et non par un horodatage : une condition de surveillance
    a trois états — vraie, fausse, inconnue. Quand la porte de courant est fermée
    (courant élevé), la condition est *inconnue*, pas fausse : l'accumulateur est
    alors laissé intact sans rien y ajouter, pour qu'une conduite alternant
    accélérations et courts arrêts ne remette jamais la temporisation à zéro.

    Le rappel périodique (`periode_rappel_s`) réémet l'événement tant que le seuil
    reste armé. Son compteur (`duree_depuis_rappel_s`) suit l'état d'armement et
    non la mesure : il avance même porte fermée et se réinitialise au désarmement.
    Une période nulle désactive le rappel (émission unique à l'armement).
    """

    nom: str
    tension_v: float
    evenement: str
    periode_rappel_s: float = 0.0
    duree_condition_s: float = 0.0
    duree_depuis_rappel_s: float = 0.0
    arme: bool = False

    @property
    def actif(self) -> bool:
        """Indique si le seuil doit être évalué."""
        return self.tension_v > 0.0


@dataclass
class ConfigurationAlerte:
    """Regroupe les paramètres purs de la logique d'alerte d'un rail."""

    courant_max_evaluation_a: float
    temporisation_s: float
    hysteresis_rearmement_v: float


@dataclass
class ResultatAlerte:
    """
    Décrit un événement produit par l'évaluation d'un seuil.

    `genre` vaut `'armement'`, `'rappel'` ou `'retablissement'`. `evenement` est le
    libellé à publier sur le topic d'événement ; il est vide pour un
    rétablissement, qui ne publie rien. `message_log` est le texte destiné au
    journal, déjà formaté par la logique pure pour rester identique à l'existant.
    """

    nom_seuil: str
    genre: str
    evenement: str
    message_log: str


def evaluer_seuils(
    seuils: list[SeuilAlerte],
    configuration: ConfigurationAlerte,
    tension_v: float,
    courant_a: float,
    pas_s: float,
) -> list[ResultatAlerte]:
    """
    Applique porte de courant, temporisation, hystérésis et rappel à chaque seuil.

    Fonction pure : elle modifie l'état des `seuils` reçus (accumulateurs,
    armement) et retourne la liste des résultats à journaliser et à publier, dans
    l'ordre où ils surviennent. Ne journalise ni ne publie rien elle-même.
    """
    resultats: list[ResultatAlerte] = []

    # Porte de courant : sous charge, la tension chute par la résistance
    # interne (V = Vfem - R_interne x I) et ne dit rien de l'état de charge.
    # Courant élevé => condition de surveillance *inconnue*, ni vraie ni
    # fausse : on ne touche alors ni à l'accumulateur ni à l'armement.
    courant_faible = abs(courant_a) < configuration.courant_max_evaluation_a

    for seuil in seuils:
        if not seuil.actif:
            continue

        if courant_faible and tension_v < seuil.tension_v:
            # Condition vraie : on accumule le temps passé sous le seuil.
            seuil.duree_condition_s += pas_s
            if not seuil.arme and seuil.duree_condition_s >= configuration.temporisation_s:
                seuil.arme = True
                seuil.duree_depuis_rappel_s = 0.0
                resultats.append(ResultatAlerte(
                    nom_seuil=seuil.nom,
                    genre='armement',
                    evenement=seuil.evenement,
                    message_log=(
                        f'seuil {seuil.nom} franchi — '
                        f'{tension_v:.2f} V sous {seuil.tension_v:.2f} V, '
                        f'courant {courant_a:.2f} A, maintenu '
                        f'{configuration.temporisation_s:.0f} s.'
                    ),
                ))
        elif courant_faible:
            # Condition fausse : la tension est au-dessus du seuil. On repart
            # de zéro. Le désarmement exige en plus l'hystérésis complète :
            # une tension qui remonte à peine ne prouve pas la récupération.
            seuil.duree_condition_s = 0.0
            tension_rearmement_v = seuil.tension_v + configuration.hysteresis_rearmement_v
            if seuil.arme and tension_v >= tension_rearmement_v:
                seuil.arme = False
                seuil.duree_depuis_rappel_s = 0.0
                resultats.append(ResultatAlerte(
                    nom_seuil=seuil.nom,
                    genre='retablissement',
                    evenement='',
                    message_log=(
                        f'seuil {seuil.nom} rétabli — '
                        f'{tension_v:.2f} V au-dessus de {tension_rearmement_v:.2f} V.'
                    ),
                ))
        # Sinon : porte de courant fermée, mesure inconnue — on ne conclut
        # rien ici. Le rappel ci-dessous suit l'armement, pas la mesure.

        resultat_rappel = _rappeler_si_arme(seuil, pas_s)
        if resultat_rappel is not None:
            resultats.append(resultat_rappel)

    return resultats


def _rappeler_si_arme(seuil: SeuilAlerte, pas_s: float) -> ResultatAlerte | None:
    """Réémet périodiquement l'événement d'un seuil tant qu'il reste armé."""
    # Une alerte batterie est un état persistant : on la rappelle même pendant
    # que la porte de courant est fermée. Période nulle => émission unique.
    if not seuil.arme or seuil.periode_rappel_s <= 0.0:
        return None

    seuil.duree_depuis_rappel_s += pas_s
    if seuil.duree_depuis_rappel_s >= seuil.periode_rappel_s:
        seuil.duree_depuis_rappel_s = 0.0
        return ResultatAlerte(
            nom_seuil=seuil.nom,
            genre='rappel',
            evenement=seuil.evenement,
            message_log=(
                f'seuil {seuil.nom} toujours armé — '
                f'rappel après {seuil.periode_rappel_s:.0f} s.'
            ),
        )

    return None
