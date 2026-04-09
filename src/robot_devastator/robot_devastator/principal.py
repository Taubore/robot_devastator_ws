"""Nœud principal de démonstration pour générer puis jouer un audio."""

import rclpy
from rclpy.node import Node
from commun.srv import GenererAudio
from commun.srv import JouerAudio


class Principal(Node):
    """Pilote une petite séquence de test via les services audio."""

    def __init__(self):
        super().__init__('principal')
        self.generer_cli = self.create_client(GenererAudio, 'generer_audio')
        self.jouer_cli = self.create_client(JouerAudio, 'jouer_audio')
        self.nom_fichier = "bonjour_devastator"

    def attendre_services(self):
        """Attend que les deux services audio soient disponibles."""
        while not self.generer_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service 'generer_audio' non disponible, nouvelle tentative...")

        while not self.jouer_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service 'jouer_audio' non disponible, nouvelle tentative...")

    def generer_exemple(self):
        """Demande la génération d'un fichier audio d'exemple."""
        requete = GenererAudio.Request()
        requete.texte = "Bonjour. Ceci est un fichier audio pré-généré pour le robot Devastator."
        requete.nom_fichier = self.nom_fichier
        future = self.generer_cli.call_async(requete)
        rclpy.spin_until_future_complete(self, future)

        resultat = future.result()
        if resultat is None:
            self.get_logger().error("Échec de l'appel au service de génération.")
            return

        self.get_logger().info(f"Génération succès : {resultat.succes}")
        self.get_logger().info(f"Génération message : {resultat.message}")

    def jouer_exemple(self):
        """Demande la lecture du fichier audio d'exemple."""
        requete = JouerAudio.Request()
        requete.nom_fichier = self.nom_fichier
        future = self.jouer_cli.call_async(requete)
        rclpy.spin_until_future_complete(self, future)

        resultat = future.result()
        if resultat is None:
            self.get_logger().error("Échec de l'appel au service de lecture.")
            return

        self.get_logger().info(f"Lecture succès : {resultat.succes}")
        self.get_logger().info(f"Lecture message : {resultat.message}")


def main(args=None):
    """Initialise ROS 2 et exécute la séquence de démonstration."""
    rclpy.init(args=args)
    node = Principal()

    # 1. Attendre que les services ROS 2 nécessaires soient disponibles.
    node.attendre_services()

    # 2. Générer un exemple de fichier audio.
    node.generer_exemple()

    # 3. Jouer deux fois le fichier généré.
    node.jouer_exemple()
    node.jouer_exemple()

    # 4. Garder le nœud actif si d'autres interactions doivent suivre.
    rclpy.spin(node)

if __name__ == '__main__':
    main()
