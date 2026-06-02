### 2026-06-02 — Validation des angles de tourelle

**Objectif :**
Confirmer l'association physique entre les angles de servo configurés et les côtés gauche / droite.

**Résultat observé :**
- `45°` oriente la tourelle vers la gauche.
- `140°` oriente la tourelle vers la droite.
- `95°` reste l'angle central utilisé par l'autonomie simple.

**Décision :**
- La configuration active est cohérente avec le montage physique.
- Aucun correctif de code ou de YAML n'est requis pour les angles de tourelle.

### 2026-06-01 — Évitement d’obstacles avec tourelle ultrason

**Objectif :**
Valider le comportement d’autonomie simple avec avance, détection d’obstacle,
balayage gauche/droite, rotation vers le côté dégagé et reprise.

**Configuration :**
- Raspberry Pi 4 avec ROS 2 Jazzy
- Pico WH relié en UART
- Moteurs FIT0521 via MDD3A
- Capteur Grove Ultrasonic Ranger monté sur tourelle servo
- Lancement : `autonomie_simple.launch.yaml`

**Résultat observé :**
Le robot avance, détecte les obstacles, arrête les moteurs, balaie avec la tourelle,
choisit un côté, tourne et reprend l’avance. Le comportement est basique, mais
fonctionne correctement. S'il tourne trop longtemps, après un délai, il va reculer un peu
et reprendre.

**Décision :**
- Acquis : chaîne autonomie ultrason + tourelle + moteurs fonctionnelle.
- À corriger : rien de bloquant observé pour un robot avec un simple sonar.
- À surveiller : précision des virages, comportement dans les coins, obstacles bas non détectables.
