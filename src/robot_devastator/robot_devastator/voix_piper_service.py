import rclpy
from rclpy.node import Node
from commun.srv import Parler 
import subprocess
import os

class VoixPiper(Node):
    def __init__(self):
        super().__init__('voix_piper')

        # Déclare des paramètres ROS pour le modèle Piper
        self.declare_parameter('piper_model', '/opt/piper/voix/fr_FR-siwis-low.onnx')
        self.declare_parameter('piper_config', '/opt/piper/voix/fr_FR-siwis-low.onnx.json')
        self.declare_parameter('audio_output', '/tmp/sortie.wav')

        self.piper_model = self.get_parameter('piper_model').get_parameter_value().string_value
        self.piper_config = self.get_parameter('piper_config').get_parameter_value().string_value
        self.audio_output = self.get_parameter('audio_output').get_parameter_value().string_value

        self.srv = self.create_service(Parler, 'parler', self.parler_callback)
        self.get_logger().info("Service 'parler' prêt.")

    def parler_callback(self, request, response):
        texte = request.texte.strip()
        if not texte:
            response.succes = False
            response.message = "Le texte fourni est vide."
            return response

        self.get_logger().info(f"Texte reçu : {texte}")

        try:
            subprocess.run(
                [
                    '/usr/local/bin/piper',
                    '--model', self.piper_model,
                    '--config', self.piper_config,
                    '--output_file', self.audio_output
                ],
                input=texte,
                text=True,
                check=True,
                timeout=10
            )
            if not os.path.isfile(self.audio_output):
                raise FileNotFoundError(f"Fichier audio non généré : {self.audio_output}")

            subprocess.run(['aplay', self.audio_output], check=True)
            response.succes = True
            response.message = f"Piper a parlé: {texte}"

        except subprocess.TimeoutExpired:
            response.succes = False
            response.message = "Le processus Piper a dépassé le délai d'exécution."
        except subprocess.CalledProcessError as e:
            response.succes = False
            response.message = f"Erreur lors de l'exécution de Piper : {e}"
        except Exception as e:
            response.succes = False
            response.message = f"Erreur inattendue : {e}"

        return response

def main(args=None):
    rclpy.init(args=args)
    node = VoixPiper()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
