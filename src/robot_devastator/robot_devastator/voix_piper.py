import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger  # Simple service pour test
import subprocess

class VoixPiper(Node):
    def __init__(self):
        super().__init__('voix_piper')
        self.srv = self.create_service(Trigger, 'parler', self.parler_callback)

    def parler_callback(self, request, response):
        texte = "Enfin ça fonctionne et je peux intégrer la voix pour mon robot!"
        try:
            result = subprocess.run(
                [
                    '/usr/local/bin/piper',
                    '--model', '/opt/piper/fr_FR-siwis-low.onnx',
                    '--config', '/opt/piper/fr_FR-siwis-low.onnx.json',
                    '--output_file', '/tmp/sortie.wav'
                ],
                input=texte,
                text=True,          # pour envoyer "texte" comme chaîne UTF-8
                check=True,
                timeout=10
            )
            subprocess.run(['aplay', '/tmp/sortie.wav'], check=True)
            response.success = True
            response.message = f"Piper a parlé: {texte}"
        except Exception as e:
            response.success = False
            response.message = str(e)
        
        return response

def main(args=None):
    rclpy.init(args=args)
    node = VoixPiper()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main() 