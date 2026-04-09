"""Nœud principal du robot."""

import rclpy
from rclpy.node import Node
from commun.srv import GenererAudio
from commun.srv import JouerAudio


class Principal(Node):
    """Orchestration des activités du robot."""

    def __init__(self):
        super().__init__('principal')
        self.generer_cli = self.create_client(GenererAudio, 'generer_audio')
        self.jouer_cli = self.create_client(JouerAudio, 'jouer_audio')

    def attendre_services(self):
        """Attend que tous les services soient disponibles."""
        while not self.generer_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service 'generer_audio' non disponible, nouvelle tentative...")

        while not self.jouer_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service 'jouer_audio' non disponible, nouvelle tentative...")

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
    
    # 4. Garder le nœud actif si d'autres interactions doivent suivre.
    rclpy.spin(node)

if __name__ == '__main__':
    main()
