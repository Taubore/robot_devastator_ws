import rclpy
from rclpy.node import Node
from robot_devastator.srv import Parler

class Principal(Node):
    def __init__(self):
        super().__init__('principal')
        self.cli = self.create_client(Parler, 'parler')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service non disponible, nouvelle tentative...")

        self.req = Parler.Request()
        self.req.texte = "Enfin ça fonctionne et je peux intégrer la voix pour mon robot!"
        self.envoyer_texte()

    def envoyer_texte(self):
        self.future = self.cli.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        if self.future.result() is not None:
            self.get_logger().info(f"Succès: {self.future.result().succes}")
            self.get_logger().info(f"Message: {self.future.result().message}")
        else:
            self.get_logger().error("Échec de l'appel au service.")        

def main(args=None):
    rclpy.init(args=args)
    node = Principal()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
