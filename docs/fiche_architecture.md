# Fiche d’architecture Devastator v1 — brouillon

## 1. Objectif du robot

Devastator est un robot mobile servant de plateforme d’apprentissage de robototique avec ROS 2, de l'électronique et des systèmes embarqués.

La cible pédagogique finale est que ce robot mobile à chenille expérimental aura les capacités suivantes : 
1. autonomie simple d’évitement d’obstacle, puis exploration progressive de la navigation ROS 2 à l'aide de différents capteurs
2. réagir vocalement et en français à différents événements
3. capable de détecter qu'il est bloqué et de se sortir lui-même de la plupart de ces blocages
4. recevoir via un mini clavier USB certains ordres ou des mise à jour en temps réel de ses paramètres
5. "voir" son environnement à l'aide d'un module RP LiDAR et d'une caméra 3D (intégration minimale)
6. permettre de consulter certains statuts du robot via un écran LCD 2 pouces
7. afficher un demi visage (nez et bouche, car les yeux du robot sont le capteur sonar juste au dessus de l'écran LCD) du robot sur le même écran LCD.

## 2. Périmètre actuel

Autonomie simple d’évitement d’obstacle : fonctionnelle mais expérimentale.
Annonces audio françaises : fonctionnelles pour quelques événements.
Encodeurs : interface ROS 2 présente, intégration comportementale/diagnostic en cours.

## 3. Matériel impliqué actuellement

Ce matériel est celui actuellement utilisé et concerné par la version en cours de développement :
- Raspberry Pi 4 : exécution ROS 2.
- Raspberry Pi Pico WH : interface bas niveau.
- Moteurs FIT0521 : moteurs DC avec encodeurs.
- MDD3A : contrôleur moteur 2 canaux.
- Alimentation 5 V et 3,3 V par des régulateurs Pololu.
- Capteur ultrason : mesure de distance frontale, à gauche et à droite avec la tourelle.
- Servo de tourelle : orientation du capteur ultrason.
- Haut-parleur + Piper : annonces audio.

## 4. Packages ROS 2 et responsabilités

- `commun` : définit les messages et services personnalisés partagés par les autres packages.
- `interface_pico` : relie ROS 2 au Pico WH par UART pour les moteurs, la tourelle et la distance ultrason.
- `robot_devastator` : comportements propres à Devastator, dont l'autonomie et les annonces audio.
- `robot_devastator_bringup` : assemblage des nœuds, fichiers launch et paramètres YAML.

## 5. Nœuds actifs et responsabilités

- `interface_pico` : traduit les commandes ROS 2 vers UART et publie les états Pico et s'assure d'un arrêt sécuritaire des moteur s'il ne reçoit pas de nouvelle consigne à l'intérieur de 0.5 s
- `annonces_audio`: prépare les annonces audio et les joue selon les événements du robot en demandant au noeud `voix_piper`.
- `evitement_obstacle` : Nœud expérimental d'autonomie simple qui permet au robot d'éviter les obstacles.
- `voix_piper`: Génère et joue les fichiers WAV avec Piper.

## 6. Flux principaux

Commande moteur :



Mesure ultrason :



Audio :



Exemple à supprimer
---
Commande moteur :

`evitement_obstacle`
→ `/pico/commande_moteurs`
→ `interface_pico`
→ UART
→ Pico WH
→ MDD3A
→ moteurs

Mesure ultrason :

Capteur ultrason
→ Pico WH
→ UART
→ `interface_pico`
→ `/pico/distance_ultrason_mm`
→ `evitement_obstacle`

Audio :

`evitement_obstacle`
→ `/robot/evenement`
→ `annonces_audio`
→ `/generer_audio` ou `/jouer_audio`
→ `voix_piper`


## 7. Topics et services critiques

## 8. Règles de sécurité

## 9. Points de validation

## 10. Questions ouvertes