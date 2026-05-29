"""Nœud principal du robot."""

import time

import rclpy
from commun.msg import ConsigneMoteurs
from rclpy.client import Client
from rclpy.node import Node
from std_srvs.srv import Trigger

TOPIC_COMMANDE_MOTEURS = '/pico/commande_moteurs'
SERVICE_PING = '/pico/ping'
SERVICE_STOP = '/pico/stop'


class Principal(Node):
    """Nœud principal utilisé pour valider la chaîne moteur ROS 2."""

    DELAI_ATTENTE_SERVICE_S = 20.0

    def __init__(self) -> None:
        super().__init__('principal')
        self.ping_pico_cli = self.create_client(Trigger, SERVICE_PING)
        self.stop_pico_cli = self.create_client(Trigger, SERVICE_STOP)
        self.consigne_moteurs_pub = self.create_publisher(
            ConsigneMoteurs,
            TOPIC_COMMANDE_MOTEURS,
            10,
        )

    def attendre_service(self, client: Client, nom_service: str) -> None:
        """Attend un service pendant un temps borné pour éviter une boucle infinie."""
        echeance = time.monotonic() + self.DELAI_ATTENTE_SERVICE_S
        while not client.wait_for_service(timeout_sec=1.0):
            if time.monotonic() >= echeance:
                raise RuntimeError(
                    f"Service '{nom_service}' indisponible après "
                    f"{self.DELAI_ATTENTE_SERVICE_S:.0f} s."
                )
            self.get_logger().warn(
                f"Service '{nom_service}' non disponible, nouvelle tentative..."
            )

    def appeler_service_trigger(self, client: Client, nom_service: str) -> bool:
        """Appelle un service `Trigger` et journalise son résultat."""
        requete = Trigger.Request()
        future = client.call_async(requete)
        rclpy.spin_until_future_complete(self, future)

        resultat = future.result()
        if resultat is None:
            self.get_logger().error(f"Échec de l'appel au service '{nom_service}'.")
            return False

        if not resultat.success:
            self.get_logger().error(
                f"Le service '{nom_service}' a répondu en échec : {resultat.message}"
            )
            return False

        self.get_logger().info(f"Service '{nom_service}' : {resultat.message}")
        return True

    def publier_consigne_moteurs(self, gauche: int, droite: int) -> None:
        """Publie une consigne moteur simple vers l'interface Pico."""
        message = ConsigneMoteurs()
        message.gauche = gauche
        message.droite = droite
        self.consigne_moteurs_pub.publish(message)
        self.get_logger().info(
            f"Consigne moteurs publiée : gauche={gauche}, droite={droite}"
        )

    def arreter_moteurs(self) -> None:
        """Envoie une consigne d'arrêt explicite, puis demande l'arrêt au Pico."""
        self.publier_consigne_moteurs(0, 0)
        self.appeler_service_trigger(self.stop_pico_cli, SERVICE_STOP)

    def tester_moteurs_demarrage(self) -> None:
        """Envoie quelques consignes courtes pour valider le chemin ROS 2 vers le Pico."""
        self.get_logger().info("Début du test de démarrage des moteurs.")

        if not self.appeler_service_trigger(self.ping_pico_cli, SERVICE_PING):
            return

        # Une courte pause laisse le temps à la découverte ROS 2 du topic
        # `/pico/commande_moteurs` de se stabiliser avant la première publication.
        time.sleep(0.2)

        sequence_test = [
            ("avance", 500, 500, 3.0),
            ("rotation sur place", 500, -500, 3.0),
            ("recul", -500, -500, 3.0),
            ("arrêt", 0, 0, 1.0),
        ]

        try:
            for description, gauche, droite, duree_s in sequence_test:
                self.get_logger().info(f"Test moteurs : {description}.")
                self.publier_consigne_moteurs(gauche, droite)
                time.sleep(duree_s)
        finally:
            self.arreter_moteurs()

        self.get_logger().info("Fin du test de démarrage des moteurs.")


def main(args: list[str] | None = None) -> None:
    """Initialise ROS 2 et exécute la séquence de validation moteur."""
    rclpy.init(args=args)
    node = Principal()

    try:
        # Attendre que les services ROS 2 nécessaires soient disponibles.
        node.attendre_service(node.ping_pico_cli, SERVICE_PING)
        node.attendre_service(node.stop_pico_cli, SERVICE_STOP)

        # Tester rapidement la chaîne ROS 2 -> Pico avec quelques consignes moteurs.
        node.tester_moteurs_demarrage()
    except KeyboardInterrupt:
        node.get_logger().info("Arrêt demandé par l'utilisateur.")
    except RuntimeError as erreur:
        node.get_logger().error(str(erreur))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
