"""Services ROS 2 pour générer et jouer des fichiers audio via Piper."""

import os
import subprocess
from pathlib import Path

import rclpy
from rclpy.node import Node

from commun.srv import GenererAudio
from commun.srv import JouerAudio

PIPER_EXECUTABLE = '/usr/local/bin/piper'
AUDIO_TEMP_DIR = Path('/tmp')


class VoixPiper(Node):
    """Expose les services ROS 2 de génération et de lecture audio."""

    def __init__(self):
        super().__init__('voix_piper')

        # Ces paramètres permettent de changer le modèle ou le chemin de sortie
        # sans modifier le code Python.
        self.declare_parameter('piper_model', '/opt/piper/voix/fr_FR-siwis-low.onnx')
        self.declare_parameter('piper_config', '/opt/piper/voix/fr_FR-siwis-low.onnx.json')
        self.declare_parameter('audio_output', '/tmp/derniere_sortie.wav')

        self.piper_model = self.get_parameter('piper_model').get_parameter_value().string_value
        self.piper_config = self.get_parameter('piper_config').get_parameter_value().string_value
        self.audio_output = Path(
            self.get_parameter('audio_output').get_parameter_value().string_value
        )

        self.generer_srv = self.create_service(
            GenererAudio,
            'generer_audio',
            self.generer_audio_callback
        )
        self.jouer_srv = self.create_service(
            JouerAudio,
            'jouer_audio',
            self.jouer_audio_callback
        )
        self.get_logger().info("Services 'generer_audio' et 'jouer_audio' prêts.")

    def _resoudre_chemin_audio(self, nom_fichier=None):
        """Retourne le chemin audio cible à partir d'un nom simple."""
        if nom_fichier:
            if '/' in nom_fichier or '\\' in nom_fichier:
                raise ValueError("Le nom de fichier doit être un nom simple, sans chemin.")
            return AUDIO_TEMP_DIR / f"{nom_fichier}.wav"
        return self.audio_output

    def generer_audio_callback(self, request, response):
        """Génère un fichier audio à partir du texte reçu par le service."""
        texte = request.texte.strip()
        nom_fichier = request.nom_fichier.strip()

        if not texte:
            response.succes = False
            response.message = "Le texte fourni est vide."
            response.chemin_fichier = ""
            return response

        self.get_logger().info("Génération audio demandée.")

        try:
            chemin_audio = self._resoudre_chemin_audio(nom_fichier or None)

            subprocess.run(
                [
                    PIPER_EXECUTABLE,
                    '--model', self.piper_model,
                    '--config', self.piper_config,
                    '--output_file', str(chemin_audio),
                ],
                input=texte,
                text=True,
                check=True,
                timeout=10,
            )

            if not os.path.isfile(chemin_audio):
                raise FileNotFoundError(f"Fichier audio non généré : {chemin_audio}")

            response.succes = True
            response.message = f"Fichier audio généré : {chemin_audio}"
            response.chemin_fichier = str(chemin_audio)
        except ValueError as erreur:
            response.succes = False
            response.message = str(erreur)
            response.chemin_fichier = ""
        except subprocess.TimeoutExpired:
            response.succes = False
            response.message = "Le processus Piper a dépassé le délai d'exécution."
            response.chemin_fichier = ""
        except subprocess.CalledProcessError as erreur:
            response.succes = False
            response.message = f"Erreur lors de l'exécution de Piper : {erreur}"
            response.chemin_fichier = ""
        except FileNotFoundError as erreur:
            response.succes = False
            response.message = str(erreur)
            response.chemin_fichier = ""
        except Exception as erreur:
            response.succes = False
            response.message = f"Erreur inattendue : {erreur}"
            response.chemin_fichier = ""

        return response

    def jouer_audio_callback(self, request, response):
        """Joue un fichier audio existant demandé par le service."""
        nom_fichier = request.nom_fichier.strip()

        try:
            chemin_audio = self._resoudre_chemin_audio(nom_fichier or None)

            if not os.path.isfile(chemin_audio):
                raise FileNotFoundError(f"Fichier audio introuvable : {chemin_audio}")

            subprocess.run(['aplay', str(chemin_audio)], check=True, timeout=10)

            response.succes = True
            response.message = f"Lecture audio lancée : {chemin_audio}"
            response.chemin_fichier = str(chemin_audio)
        except ValueError as erreur:
            response.succes = False
            response.message = str(erreur)
            response.chemin_fichier = ""
        except subprocess.TimeoutExpired:
            response.succes = False
            response.message = "La lecture audio a dépassé le délai d'exécution."
            response.chemin_fichier = ""
        except subprocess.CalledProcessError as erreur:
            response.succes = False
            response.message = f"Erreur lors de la lecture audio : {erreur}"
            response.chemin_fichier = ""
        except FileNotFoundError as erreur:
            response.succes = False
            response.message = str(erreur)
            response.chemin_fichier = ""
        except Exception as erreur:
            response.succes = False
            response.message = f"Erreur inattendue : {erreur}"
            response.chemin_fichier = ""

        return response


def main(args=None):
    """Initialise ROS 2 puis démarre le service audio Piper."""
    rclpy.init(args=args)

    # Ce nœud expose deux services : un pour générer un fichier audio,
    # l'autre pour le relire plus tard.
    node = VoixPiper()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
