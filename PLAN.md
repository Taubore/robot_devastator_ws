# Plan de formation Devastator

## Règles

- Une case se coche uniquement après test observable sur le robot réel ou validation explicite.
- Une note courte (date + observation clé) peut accompagner chaque case cochée.
- L'ordre des phases est indicatif. Réviser en début de phase, pas pendant.
- Claude Code coche les cases sur demande explicite uniquement.

---

## Phase 0 — Fondation (infrastructure et sécurité)

Objectif : robot lançable, contrôlable et arrêtable de façon fiable.

- [x] Chaîne UART Pi 4 → Pico WH → MDD3A → moteurs fonctionnelle
- [x] Watchdog sécurité moteur (expiration 500 ms côté Pico et côté `interface_pico`)
- [x] Contrat UART documenté (`docs/contrat_pico_ros2.md`)
- [x] Arbitre commandes moteurs (une seule source active avant `/pico/commande_moteurs`)
- [x] Téléopération clavier permanente (`teleop_clavier`)
- [x] Annonces audio (`annonces_audio` avec Piper + MAX98357)
- [x] Autonomie simple au sonar (`evitement_obstacle` — expérimental)
- [x] Validation complète `interface_pico.launch.yaml` roues dans le vide :
      ping, stop, sonar, tourelle et encodeurs

---

## Phase 1 — Consolidation documentaire

Objectif : base documentaire propre avant d'ajouter de la complexité.

- [x] `README.md` créé pour le package `commun`
- [x] `README.md` créé pour le package `robot_devastator`
- [x] `README.md` créé pour le package `robot_devastator_bringup`
- [x] `CLAUDE.md` pont créé dans `robot_devastator_ws` (redirige vers `AGENTS.md`)
- [x] `CLAUDE.md` pont créé dans `robot_devastator_pico` (redirige vers `AGENTS.md`)
- [x] `PLAN.md` intégré au dépôt et lu par Claude en séance

---

## Phase 2 — Encodeurs et diagnostic

Objectif : comprendre et valider les mesures brutes avant toute odométrie.
Notion clé : encodeur en quadrature, ticks, résolution, sens de rotation.

- [ ] Lecture des ticks bruts vérifiée sur `/pico/encodeurs` en roulant
- [ ] Cohérence gauche/droite et sens validés (avance, recul, rotation sur place)
- [ ] Nœud de diagnostic encodeurs : affichage ticks, delta, vitesse estimée
- [ ] Reset encodeurs via service `/pico/reset_encodeurs` testé et fonctionnel

---

## Phase 3 — Odométrie différentielle

Objectif : estimer la position du robot à partir des encodeurs.
Notion clé : cinématique différentielle, intégration numérique, dérive.

- [ ] Paramètres mécaniques documentés (diamètre roue, entraxe, ticks/tour)
- [ ] Nœud odométrie publiant sur `/odom` (`nav_msgs/Odometry`)
- [ ] Validation : avance ~1 m → position X ≈ 1,0 m dans `/odom`
- [ ] Validation : rotation ~90° → yaw ≈ 1,57 rad dans `/odom`

---

## Phase 4 — Description robot et visualisation

Objectif : représenter le robot dans ROS 2 et visualiser son état.
Notion clé : URDF/Xacro, TF, frames de référence, RViz.

- [ ] URDF/Xacro minimal (`base_link`, deux roues, tourelle)
- [ ] TF publié correctement (`base_footprint` → `base_link` → roues)
- [ ] RViz : modèle robot visible, repères TF cohérents
- [ ] RViz : trajectoire odométrie visible lors d'un déplacement réel

---

## Phase 5 — Sous-systèmes additionnels

Objectif : enrichir la plateforme selon utilité pédagogique réelle.
Ordre indicatif — réviser selon le besoin au moment venu.

- [ ] INA260 : mesure courant/tension publiée dans ROS 2
- [ ] LCD Waveshare 2" : affichage état ou visage robot
- [ ] RPLIDAR A1M8 : scan laser publié, visualisation RViz
- [ ] RealSense D435IF : flux profondeur publié, visualisation RViz
- [ ] ReSpeaker Mic Array v3.0 : réception vocale expérimentale

---

## Phase 6 — Navigation (décision à prendre après Phase 5)

Objectif : navigation autonome simple avec Nav2.
Dépend : odométrie stable + RPLIDAR + carte.

- [ ] Carte statique ou SLAM simple avec RPLIDAR
- [ ] Nav2 minimal : naviguer vers un point donné
- [ ] Comportement de récupération documenté et testé

## Décisions et contexte

Format : `YYYY-MM-DD — décision ou observation clé (une ligne)`

- 2026-06-22 — PLAN.md adopté comme source unique de progression.
  formation_ros2_devastator.md supprimé.  
- 2026-06-10 — Arbitre moteur validé comme point central unique avant /pico/commande_moteurs.
- 2026-06-10 — Autonomie simple (evitement_obstacle) expérimentale, démarre en mode attente.