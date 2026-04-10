"""Nœud principal du robot."""

import time

import rclpy
from commun.msg import ConsigneMoteurs
from commun.srv import GenererAudio
from commun.srv import JouerAudio
from rclpy.node import Node
from std_srvs.srv import Trigger


class Principal(Node):
    """Orchestration des activités du robot."""

    def __init__(self):
        super().__init__('principal')
        self.generer_cli = self.create_client(GenererAudio, 'generer_audio')
        self.jouer_cli = self.create_client(JouerAudio, 'jouer_audio')
        self.ping_pico_cli = self.create_client(Trigger, 'ping')
        self.stop_pico_cli = self.create_client(Trigger, 'stop')
        self.consigne_moteurs_pub = self.create_publisher(
            ConsigneMoteurs,
            'consigne_moteurs',
            10,
        )

    def attendre_services(self):
        """Attend que tous les services soient disponibles."""
        while not self.generer_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service 'generer_audio' non disponible, nouvelle tentative...")

        while not self.jouer_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service 'jouer_audio' non disponible, nouvelle tentative...")

        while not self.ping_pico_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service 'ping' non disponible, nouvelle tentative...")

        while not self.stop_pico_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service 'stop' non disponible, nouvelle tentative...")

    def generer_fichier_audio(self, texte, nom_fichier):
        """Demande la génération d'un fichier audio"""
        requete = GenererAudio.Request()
        requete.texte = texte
        requete.nom_fichier = nom_fichier
        future = self.generer_cli.call_async(requete)
        rclpy.spin_until_future_complete(self, future)

        resultat = future.result()
        if resultat is None:
            self.get_logger().error("Échec de l'appel au service de génération.")
            return

        self.get_logger().info(f"{resultat.message}")

    def jouer_wav(self, nom_fichier):
        """Demande la lecture du fichier audio d'exemple."""
        requete = JouerAudio.Request()
        requete.nom_fichier = nom_fichier
        future = self.jouer_cli.call_async(requete)
        rclpy.spin_until_future_complete(self, future)

        resultat = future.result()
        if resultat is None:
            self.get_logger().error("Échec de l'appel au service de lecture.")
            return

    def appeler_service_trigger(self, client, nom_service):
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

    def publier_consigne_moteurs(self, gauche, droite):
        """Publie une consigne moteur simple vers l'interface Pico."""
        message = ConsigneMoteurs()
        message.gauche = gauche
        message.droite = droite
        self.consigne_moteurs_pub.publish(message)
        self.get_logger().info(
            f"Consigne moteurs publiée : gauche={gauche}, droite={droite}"
        )

    def tester_moteurs_demarrage(self):
        """Envoie quelques consignes courtes pour valider le chemin ROS 2 vers le Pico."""
        self.get_logger().info("Début du test de démarrage des moteurs.")

        if not self.appeler_service_trigger(self.ping_pico_cli, 'ping'):
            return

        # Une courte pause laisse le temps à la découverte ROS 2 du topic
        # `consigne_moteurs` de se stabiliser avant la première publication.
        time.sleep(0.2)

        sequence_test = [
            ("avance lente", 200, 200, 1.0),
            ("rotation sur place", 220, -220, 1.0),
            ("recul lent", -180, -180, 1.0),
            ("arrêt", 0, 0, 0.5),
        ]

        for description, gauche, droite, duree_s in sequence_test:
            self.get_logger().info(f"Test moteurs : {description}.")
            self.publier_consigne_moteurs(gauche, droite)
            time.sleep(duree_s)

        self.appeler_service_trigger(self.stop_pico_cli, 'stop')
        self.get_logger().info("Fin du test de démarrage des moteurs.")


def main(args=None):
    """Initialise ROS 2 et exécute la séquence de démonstration."""
    rclpy.init(args=args)
    node = Principal()

    # 1. Attendre que les services ROS 2 nécessaires soient disponibles.
    node.attendre_services()

    # 2. Générer des fichiers audio.
    node.generer_fichier_audio("Je suis prêt à effectuer des mouvements.", "pret")
    node.generer_fichier_audio("Obstacle droit devant", "obstacle_1")
    node.generer_fichier_audio("Oups, il y a quelque chose", "obstacle_2")
    node.generer_fichier_audio("Je dois contourner ça", "contourner_1")
    node.generer_fichier_audio("Je contourne", "contourner_2")

    # 3. Jouer deux fois le fichier généré.
    node.jouer_wav("pret")

    # 4. Tester rapidement la chaîne ROS 2 -> Pico avec quelques consignes moteurs.
    node.tester_moteurs_demarrage()

    # 5. Garder le nœud actif si d'autres interactions doivent suivre.
    rclpy.spin(node)

if __name__ == '__main__':
    main()
