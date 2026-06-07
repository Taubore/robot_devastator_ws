# Composantes actives

| ID | Nom | Catégorie | Rôle | État | Description |
|---|---|---|---|---|---|
| RASPI4 | Raspberry Pi 4 4 GB | Nano-ordinateur | Logique haut niveau ROS 2 | Actif | Ordinateur principal du robot. Exécute ROS 2 Jazzy, coordonne les nœuds, prend les décisions haut niveau. |
| PICO_WH | Raspberry Pi Pico WH | Microcontrôleur | Bas niveau temps réel | Actif | Contrôle les moteurs, lit les signaux rapides et communique avec le Raspberry Pi 4 par UART. |
| MDD3A | Cytron MDD3A | Contrôleur moteur | Gère les moteurs | Actif | Pilote deux moteurs DC à partir des signaux PWM du Pico. |
| FIT0521_G | DFRobot FIT0521 gauche | Moteur | Traction gauche | Actif | Moteur DC 6 V avec encodeur intégré. Utilisé pour la roue gauche. |
| FIT0521_D | DFRobot FIT0521 droit | Moteur | Traction droite | Actif | Moteur DC 6 V avec encodeur intégré. Utilisé pour la roue droite. |
| ULTRASON | Grove Ultrasonic Ranger | Capteur distance | Détection obstacle | Actif | Capteur ultrason utilisé pour mesurer la distance devant le robot. Monté sur tourelle. |
| SERVO_TOUR | Hitec HS-422 | Servo | Orientation sonar | Actif | Oriente le capteur ultrason vers la gauche, le centre ou la droite. |
| BATT_LOGIQUE | NiMH Tenergy PRO — pack maison | Batterie | Alimentation logique | Actif | Pack 6 cellules NiMH 7,2 V 2800 mAh utilisé comme source principale de la logique du robot. |
| BATT_MOTEUR | NiMH Melasta | Batterie | Alimentation moteurs | Actif | Pack 5 cellules NiMH 6 V 2000 mAh utilisé comme source d'alimentation des moteurs. |
| VOLTM_LOGIQUE | Voltmètre logique | Mesure alimentation | Affichage tension | Actif | Afficheur numérique CC pour surveiller la tension d’alimentation de la batterie principale. |
| VOLTM_MOTEUR | Voltmètre moteurs | Mesure alimentation | Affichage tension | Actif | Afficheur numérique CC pour surveiller la tension d’alimentation de la batterie des moteurs. |
| BUCK_3V3 | Pololu 4090 D36V50F3 | Alimentation | Rail logique 3,3 V | Actif | Régulateur abaisseur destiné à fournir une alimentation 3,3 V / 6,5 A stable aux capteurs et modules logiques compatibles. |
| BUCK_5V | Pololu 4091 D36V50F5 | Alimentation | Rail logique 5 V | Actif | Régulateur abaisseur destiné à fournir une alimentation 5 V / 5,5 A stable aux capteurs et modules logiques du robot. |
| ALIM_LOGIQUE | Circuit d’alimentation 3,3 V / 5 V | Alimentation | Distribution logique | Actif | Circuit maison sur perfboard alimenté par la batterie logique et fournissant le 3,3 V et le 5 V au  robot. Intègre les régulateurs abaisseurs Pololu et sert de point central pour l’alimentation des modules logiques. |
| SW_LOGIQUE | Interrupteur alimentation logique | Alimentation | Mise sous tension logique | Actif | Interrupteur connecté au circuit d’alimentation maison pour contrôler manuellement la marche ou l’arrêt du courant provenant de la batterie logique. Ne commande pas l'alimentation des moteurs. |
| AUDIO_I2S | MAX98357 + PCM5102A | Audio | Amplification et conversion audio | Actif | Modules audio prévus pour générer et amplifier et donner une voix au robot avec Piper. |
| HP_BF37 | Visaton BF 37 | Audio | Sortie sonore du robot | Actif | Haut-parleur 8 Ω prévu pour la voix du robot et les retours sonores via la chaîne audio I2S. |
| CLAV_X8 | Mini clavier USB sans-fil Rii X8| Interface opérateur | Téléopération | Actif | Pour téléopératio très simple pour tests manuels. |

# Composantes acquises mais non utilisées ou mises de côté temporairement

| ID | Nom | Catégorie | Rôle | État | Description |
|---|---|---|---|---|---|
| INA260 | Adafruit INA260 | Mesure alimentation | Mesure tension/courant | Futur | Capteur de mesure courant/tension/puissance utile pour diagnostiquer l’alimentation. |
| RPLIDAR | Slamtec RPLIDAR A1M8 | Lidar | Cartographie et navigation | Gelé | Capteur réservé pour une étape ROS 2 plus avancée. |
| REALSENSE | Intel RealSense D435IF | Caméra profondeur | Perception 3D | Futur | Caméra de profondeur prévue pour étapes avancées. |
| LCD2 | Waveshare LCD 2 pouces ST7789V | Affichage | Visage / état robot | Futur | Écran prévu pour afficher l’état du robot. |
| MIC_ARRAY | ReSpeaker Mic Array v3.0 | Audio entrée | Commandes vocales | Futur | Microphone prévu pour interaction vocale avec le robot. |
| PS2 | Manette Lynxmotion PS2 | Interface opérateur | Téléopération | Gelé | Manette pouvant rendre plus facile et agréable la conduite manuelle du robot en téléopération. Non essentiel, puisque CLAV_X8 peut répondre à ces besoins tout en étant plus flexible, mais moins ergonomique pour la conduite. |

## Convention d’état

- Actif : utilisé maintenant ou en cours d'intégration à l’étape actuelle.
- Gelé : physiquement sur le robot, mais non intégré logiciellement.
- Futur : acquis, mais réservé pour plus tard.
