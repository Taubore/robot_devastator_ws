# -*- coding: utf-8 -*-
"""
Nœud ROS 2 qui surveille tension et courant des batteries via des capteurs INA260.

Pour chaque rail d'alimentation configuré, le nœud publie un
`sensor_msgs/msg/BatteryState` à cadence fixe et émet un `std_msgs/msg/String`
d'événement quand la tension reste sous un seuil assez longtemps, à courant
faible. Aucune valeur propre à un robot n'est codée ici : bus I2C, adresses,
seuils, libellés d'événement et technologie de batterie viennent tous du YAML.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Final

import rclpy
from rclpy.node import Node
from rclpy.publisher import Publisher
from sensor_msgs.msg import BatteryState
from smbus2 import SMBus
from std_msgs.msg import String

from surveillance_alimentation.ina260 import CODES_MOYENNAGE, LecteurINA260
from surveillance_alimentation.logique_alerte import (
    ConfigurationAlerte,
    evaluer_seuils,
    SeuilAlerte,
)

TAILLE_FILE_MESSAGES: Final[int] = 10

# Correspondance libellé YAML -> constante sensor_msgs/BatteryState. Le libellé
# reste en clair dans le YAML pour rendre le module lisible sur un autre robot.
TECHNOLOGIES_BATTERIE: Final[dict[str, int]] = {
    'inconnue': BatteryState.POWER_SUPPLY_TECHNOLOGY_UNKNOWN,
    'nimh': BatteryState.POWER_SUPPLY_TECHNOLOGY_NIMH,
    'lion': BatteryState.POWER_SUPPLY_TECHNOLOGY_LION,
    'lipo': BatteryState.POWER_SUPPLY_TECHNOLOGY_LIPO,
    'life': BatteryState.POWER_SUPPLY_TECHNOLOGY_LIFE,
    'nicd': BatteryState.POWER_SUPPLY_TECHNOLOGY_NICD,
    'limn': BatteryState.POWER_SUPPLY_TECHNOLOGY_LIMN,
}


@dataclass
class SurveillanceRail:
    """Regroupe la configuration et l'état d'exécution d'un rail d'alimentation."""

    nom: str
    lecteur: LecteurINA260
    publisher_etat: Publisher
    frame_id: str
    technologie: int
    signe_courant: int
    configuration: ConfigurationAlerte
    seuils: list[SeuilAlerte]
    echecs_consecutifs: int = 0
    illisible_signale: bool = False


class SurveillanceAlimentation(Node):
    """Publie l'état des batteries et alerte sur tension basse maintenue."""

    def __init__(self) -> None:
        """Charge les paramètres, ouvre le bus I2C et prépare chaque rail."""
        super().__init__('surveillance_alimentation')

        # Les valeurs par défaut permettent un lancement isolé sans YAML ; les
        # valeurs réelles du robot vivent dans
        # robot_devastator_bringup/config/surveillance_alimentation.yaml.
        self.declare_parameter('bus_i2c', 1)
        self.declare_parameter('periode_publication_s', 1.0)
        self.declare_parameter('nb_echantillons_moyenne', 64)
        self.declare_parameter('echecs_avant_erreur', 5)
        self.declare_parameter('topic_evenement', '/robot/evenement')
        self.declare_parameter('rails', ['logique', 'moteur'])

        self.bus_i2c = int(self.get_parameter('bus_i2c').value)
        self.periode_publication_s = float(
            self.get_parameter('periode_publication_s').value
        )
        self.nb_echantillons_moyenne = int(
            self.get_parameter('nb_echantillons_moyenne').value
        )
        self.echecs_avant_erreur = int(self.get_parameter('echecs_avant_erreur').value)
        self.topic_evenement = str(self.get_parameter('topic_evenement').value)
        noms_rails = list(self.get_parameter('rails').value)

        self._valider_parametres_globaux(noms_rails)

        # Bus I2C partagé par tous les capteurs. Une ouverture impossible est
        # fatale : sans bus, le nœud n'a rien à surveiller.
        try:
            self.bus: SMBus | None = SMBus(self.bus_i2c)
        except OSError as erreur:
            raise RuntimeError(
                f'Ouverture du bus I2C {self.bus_i2c} impossible : {erreur}'
            ) from erreur

        self.publisher_evenement = self.create_publisher(
            String,
            self.topic_evenement,
            TAILLE_FILE_MESSAGES,
        )

        self.rails = [self._preparer_rail(nom) for nom in noms_rails]

        self.minuterie = self.create_timer(
            self.periode_publication_s,
            self._surveiller_callback,
        )

        self.get_logger().info(
            'Surveillance alimentation initialisée : '
            f'bus I2C {self.bus_i2c}, '
            f'rails {noms_rails}, '
            f'publication toutes les {self.periode_publication_s:.1f} s.'
        )

    # --- Callbacks des timers ---

    def _surveiller_callback(self) -> None:
        """Lit chaque capteur, publie son état et évalue ses seuils d'alerte."""
        for rail in self.rails:
            self._traiter_rail(rail)

    # --- Méthodes privées utilitaires ---

    def _valider_parametres_globaux(self, noms_rails: list[str]) -> None:
        """Vérifie les paramètres globaux qui rendraient la configuration incohérente."""
        if self.periode_publication_s <= 0.0:
            raise ValueError("Le paramètre 'periode_publication_s' doit être positif.")
        if self.echecs_avant_erreur < 1:
            raise ValueError(
                "Le paramètre 'echecs_avant_erreur' doit valoir au moins 1."
            )
        if self.nb_echantillons_moyenne not in CODES_MOYENNAGE:
            raise ValueError(
                "Le paramètre 'nb_echantillons_moyenne' doit valoir une des tailles "
                f'AVG du INA260 : {sorted(CODES_MOYENNAGE)}.'
            )
        if not noms_rails:
            raise ValueError("Le paramètre 'rails' ne peut pas être vide.")

    def _preparer_rail(self, nom: str) -> SurveillanceRail:
        """Construit un rail à partir de ses paramètres et prépare son capteur."""
        prefixe = f'rail.{nom}'
        self.declare_parameter(f'{prefixe}.adresse_i2c', 0x40)
        self.declare_parameter(f'{prefixe}.topic', f'/alimentation/{nom}')
        self.declare_parameter(f'{prefixe}.frame_id', f'alim_{nom}')
        self.declare_parameter(f'{prefixe}.technologie', 'nimh')
        self.declare_parameter(f'{prefixe}.signe_courant', 1)
        self.declare_parameter(f'{prefixe}.seuil_avertissement_v', 0.0)
        self.declare_parameter(f'{prefixe}.seuil_critique_v', 0.0)
        self.declare_parameter(f'{prefixe}.hysteresis_rearmement_v', 0.15)
        self.declare_parameter(f'{prefixe}.courant_max_evaluation_a', 1.0)
        self.declare_parameter(f'{prefixe}.temporisation_s', 5.0)
        self.declare_parameter(f'{prefixe}.periode_rappel_avertissement_s', 0.0)
        self.declare_parameter(f'{prefixe}.periode_rappel_critique_s', 0.0)
        self.declare_parameter(f'{prefixe}.evenement_avertissement', '')
        self.declare_parameter(f'{prefixe}.evenement_critique', '')

        adresse = int(self.get_parameter(f'{prefixe}.adresse_i2c').value)
        topic = str(self.get_parameter(f'{prefixe}.topic').value)
        frame_id = str(self.get_parameter(f'{prefixe}.frame_id').value)
        technologie_libelle = str(
            self.get_parameter(f'{prefixe}.technologie').value
        ).lower()
        signe_courant = int(self.get_parameter(f'{prefixe}.signe_courant').value)
        seuil_avert_v = float(
            self.get_parameter(f'{prefixe}.seuil_avertissement_v').value
        )
        seuil_crit_v = float(self.get_parameter(f'{prefixe}.seuil_critique_v').value)
        hysteresis_v = float(
            self.get_parameter(f'{prefixe}.hysteresis_rearmement_v').value
        )
        courant_max_a = float(
            self.get_parameter(f'{prefixe}.courant_max_evaluation_a').value
        )
        temporisation_s = float(self.get_parameter(f'{prefixe}.temporisation_s').value)
        periode_rappel_avert_s = float(
            self.get_parameter(f'{prefixe}.periode_rappel_avertissement_s').value
        )
        periode_rappel_crit_s = float(
            self.get_parameter(f'{prefixe}.periode_rappel_critique_s').value
        )
        evenement_avert = str(
            self.get_parameter(f'{prefixe}.evenement_avertissement').value
        )
        evenement_crit = str(
            self.get_parameter(f'{prefixe}.evenement_critique').value
        )

        if technologie_libelle not in TECHNOLOGIES_BATTERIE:
            raise ValueError(
                f"Technologie de batterie inconnue pour le rail '{nom}' : "
                f"'{technologie_libelle}'. Valeurs permises : "
                f'{sorted(TECHNOLOGIES_BATTERIE)}.'
            )
        # Le contrat sensor_msgs/BatteryState veut un courant négatif en décharge.
        # Le sens dépend du câblage VIN+/VIN- de chaque INA260 : on corrige par un
        # facteur ±1 propre au rail, jamais par une négation codée en dur.
        if signe_courant not in (1, -1):
            raise ValueError(
                f"Rail '{nom}' : 'signe_courant' doit valoir 1 ou -1, "
                f'pas {signe_courant}.'
            )
        if (
            seuil_avert_v > 0.0
            and seuil_crit_v > 0.0
            and seuil_crit_v > seuil_avert_v
        ):
            self.get_logger().warn(
                f"Rail '{nom}' : le seuil critique ({seuil_crit_v:.2f} V) est "
                f"au-dessus du seuil d'avertissement ({seuil_avert_v:.2f} V)."
            )

        seuils = [
            SeuilAlerte(
                'avertissement', seuil_avert_v, evenement_avert, periode_rappel_avert_s
            ),
            SeuilAlerte(
                'critique', seuil_crit_v, evenement_crit, periode_rappel_crit_s
            ),
        ]

        rail = SurveillanceRail(
            nom=nom,
            lecteur=LecteurINA260(self.bus, adresse),
            publisher_etat=self.create_publisher(
                BatteryState, topic, TAILLE_FILE_MESSAGES
            ),
            frame_id=frame_id,
            technologie=TECHNOLOGIES_BATTERIE[technologie_libelle],
            signe_courant=signe_courant,
            configuration=ConfigurationAlerte(
                courant_max_evaluation_a=courant_max_a,
                temporisation_s=temporisation_s,
                hysteresis_rearmement_v=hysteresis_v,
            ),
            seuils=seuils,
        )

        # Identification et moyennage au démarrage. Un capteur absent ne doit pas
        # empêcher le nœud de démarrer pour l'autre rail : on marque le rail
        # dégradé et la minuterie retentera les lectures à chaque cycle.
        try:
            rail.lecteur.verifier_identite()
            rail.lecteur.configurer_moyennage(self.nb_echantillons_moyenne)
            self.get_logger().info(
                f"Rail '{nom}' : INA260 détecté à l'adresse 0x{adresse:02X}, "
                f'moyennage {self.nb_echantillons_moyenne} échantillons.'
            )
        except (OSError, RuntimeError) as erreur:
            rail.echecs_consecutifs = self.echecs_avant_erreur
            rail.illisible_signale = True
            self.get_logger().error(
                f"Rail '{nom}' : INA260 injoignable au démarrage à l'adresse "
                f'0x{adresse:02X} ({erreur}). Publication en état inconnu ; '
                'nouvelle tentative à chaque cycle.'
            )

        return rail

    def _traiter_rail(self, rail: SurveillanceRail) -> None:
        """Lit un capteur, publie son BatteryState et met à jour ses alertes."""
        try:
            tension_v = rail.lecteur.lire_tension_v()
            # Signe ramené au contrat BatteryState (négatif en décharge) selon le
            # câblage du capteur ; la logique d'alerte travaille sur abs(courant).
            courant_a = rail.lecteur.lire_courant_a() * rail.signe_courant
        except OSError as erreur:
            self._gerer_echec_lecture(rail, erreur)
            return

        # Lecture réussie : signaler un rétablissement puis repartir de zéro.
        if rail.echecs_consecutifs > 0:
            self.get_logger().warn(
                f"Rail '{rail.nom}' : capteur de nouveau lisible après "
                f'{rail.echecs_consecutifs} échec(s).'
            )
            rail.echecs_consecutifs = 0
            rail.illisible_signale = False

        self._publier_etat(
            rail,
            tension_v,
            courant_a,
            BatteryState.POWER_SUPPLY_STATUS_DISCHARGING,
        )
        self._evaluer_alertes(rail, tension_v, courant_a)

    def _gerer_echec_lecture(self, rail: SurveillanceRail, erreur: OSError) -> None:
        """Compte l'échec, journalise selon sa gravité et publie un état inconnu."""
        rail.echecs_consecutifs += 1

        if rail.echecs_consecutifs < self.echecs_avant_erreur:
            # Erreur transitoire : un WARN par cycle raté, jamais de mesure.
            self.get_logger().warn(
                f"Rail '{rail.nom}' : lecture I2C en échec "
                f'({rail.echecs_consecutifs}/{self.echecs_avant_erreur}) : {erreur}'
            )
        elif not rail.illisible_signale:
            # Échec durable : un seul ERROR, puis silence jusqu'au rétablissement.
            self.get_logger().error(
                f"Rail '{rail.nom}' : capteur illisible durablement après "
                f'{rail.echecs_consecutifs} tentatives ({erreur}). '
                "L'autre rail continue d'être publié."
            )
            rail.illisible_signale = True

        # On publie quand même pour garder le topic vivant et signaler la panne.
        self._publier_etat(
            rail,
            math.nan,
            math.nan,
            BatteryState.POWER_SUPPLY_STATUS_UNKNOWN,
        )

    def _publier_etat(
        self,
        rail: SurveillanceRail,
        tension_v: float,
        courant_a: float,
        statut: int,
    ) -> None:
        """Publie le BatteryState courant d'un rail."""
        message = BatteryState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = rail.frame_id
        message.voltage = float(tension_v)
        message.current = float(courant_a)

        # La courbe de décharge d'un accu NiMH est trop plate (~1,2 V/cellule sur
        # l'essentiel de la capacité) pour convertir une tension en pourcentage
        # de charge honnête. On laisse donc percentage — et les autres champs de
        # capacité — à NaN plutôt que de publier une estimation trompeuse : la
        # surveillance repose sur des seuils de tension absolus.
        message.percentage = math.nan
        message.charge = math.nan
        message.capacity = math.nan
        message.design_capacity = math.nan
        message.temperature = math.nan

        message.power_supply_status = statut
        message.power_supply_health = BatteryState.POWER_SUPPLY_HEALTH_UNKNOWN
        message.power_supply_technology = rail.technologie
        message.present = statut != BatteryState.POWER_SUPPLY_STATUS_UNKNOWN

        rail.publisher_etat.publish(message)

    def _evaluer_alertes(
        self,
        rail: SurveillanceRail,
        tension_v: float,
        courant_a: float,
    ) -> None:
        """Délègue l'évaluation des seuils à la logique pure, puis journalise et publie."""
        resultats = evaluer_seuils(
            rail.seuils,
            rail.configuration,
            tension_v,
            courant_a,
            self.periode_publication_s,
        )

        for resultat in resultats:
            self.get_logger().warn(f"Rail '{rail.nom}' : {resultat.message_log}")
            if resultat.genre in ('armement', 'rappel'):
                self._publier_evenement(resultat.evenement)

    def _publier_evenement(self, evenement: str) -> None:
        """Publie un libellé d'événement, sauf s'il est vide (événement désactivé)."""
        if not evenement.strip():
            return

        message = String()
        message.data = evenement
        self.publisher_evenement.publish(message)

    # --- Cycle de vie du nœud ---

    def fermer(self) -> None:
        """Ferme le bus I2C partagé."""
        if self.bus is not None:
            try:
                self.bus.close()
            except OSError:
                pass
            self.bus = None


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2 puis exécute le nœud jusqu'à son arrêt."""
    rclpy.init(args=args)
    noeud: SurveillanceAlimentation | None = None

    try:
        noeud = SurveillanceAlimentation()
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
