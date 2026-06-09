# À retenir
- subscription : quand ROS me parle
- publisher : je parle à ROS
- service : on me pose une question ponctuelle
- timer : je fais quelque chose régulièrement

# Éléments ROS 2
| Élément | Description courte |
|---|---|
| Workspace | Dossier global du projet ROS 2. |
| Package | Module ROS 2 contenant du code, des interfaces ou des fichiers. |
| Node | Programme ROS 2 qui fait une tâche précise. |
| Topic | Flux de données publié/écouté en continu. |
| Message | Format des données envoyées sur un topic. |
| Publisher | Partie d’un node qui publie sur un topic. |
| Subscriber | Partie d’un node qui écoute un topic. |
| Service | Demande ponctuelle avec réponse. |
| Action | Tâche longue avec progression, annulation et résultat. |
| Parameter | Réglage d’un node sans modifier le code. |
| Launch file | Fichier qui démarre un ou plusieurs nodes. |
| Interface | Définition `.msg`, `.srv` ou `.action`. |
| QoS | Règles de fiabilité et de transport des messages. |
| TF | Relations spatiales entre les parties du robot. |
| URDF | Description physique du robot. |
| Xacro | URDF paramétrable et réutilisable. |
| Bag | Enregistrement de topics pour rejouer un test. |
| RViz | Visualisation ROS 2. |
| Nav2 | Navigation autonome avancée. |

# Types standards
ROS 2 contient beaucoup de types standards. Ils sont organisés par packages.

Les plus importants sont :

std_msgs            messages simples : String, Int32, Bool, Float32, etc.
std_srvs            services simples : Empty, SetBool, Trigger
geometry_msgs       positions, orientations, vecteurs, Twist, Pose
sensor_msgs         données capteurs : LaserScan, Image, Imu, Range, JointState
nav_msgs            odométrie, chemins, cartes
diagnostic_msgs     diagnostics système
visualization_msgs  affichage dans RViz
trajectory_msgs     trajectoires

Utilise un type standard quand il décrit déjà bien ton besoin. Crée un type personnalisé seulement quand le standard ne suffit pas.

Exemples appliqués à Devastator :

/pico/distance_ultrason_mm
Type actuel : std_msgs/msg/Int32
Acceptable pour l’instant, car tu veux juste une distance simple en mm.

/pico/commande_tourelle_deg
Type actuel : std_msgs/msg/Int32
Acceptable pour l’instant, car tu veux juste un angle entier.

/pico/etat
Type actuel : std_msgs/msg/String
Acceptable pour du diagnostic brut.

/pico/ping
Type : std_srvs/srv/Trigger
Très approprié.

/pico/stop_moteurs
Type : std_srvs/srv/Trigger
Très approprié.

/pico/commande_moteurs
Type : commun/msg/ConsigneMoteurs
Approprié, car tu as deux valeurs liées : gauche et droite.

À moyen terme, certains types standards pourraient devenir plus pertinents. Par exemple, si ton sonar devient un vrai capteur ROS 2 mieux structuré, sensor_msgs/msg/Range serait plus expressif que std_msgs/msg/Int32, parce qu’il peut porter une distance avec un contexte de capteur. Mais ne change pas maintenant : pour ton étape actuelle, Int32 en millimètres est simple, testable et suffisant.
