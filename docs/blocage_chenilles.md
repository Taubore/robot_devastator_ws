# Blocage de chenilles — mode de défaillance connu

Le blocage de chenilles est un mode de défaillance **récurrent** de la plateforme Devastator,
inhérent à sa mécanique (chenilles plastique, deux moteurs FIT0521 6 V, entraînement direct sans
limiteur de couple). Il faut le considérer comme un comportement attendu de la plateforme, pas
comme un incident exceptionnel.

## Description

Une ou les deux chenilles se retrouvent immobilisées alors qu'une consigne moteur non nulle est
maintenue : obstacle infranchissable, coincement contre un mur, objet pris dans le barbotin,
sol trop adhérent en rotation sur place. Le moteur reste sous tension, à rotor bloqué.

## Conséquences observées

- **Courant maximal du robot.** Les deux chenilles bloquées à consigne 1000 tirent environ
  **6,5 A** sur le rail moteur, contre ~0,5 A en rotation libre et ~1,25 A en charge partielle
  (voir [parametres.md](parametres.md)). C'est le pire cas de consommation de la plateforme.
- **Échauffement du câblage de masse.** Un blocage prolongé a déjà provoqué un échauffement
  visible du câblage de masse du rail moteur. Un **fusible rapide 10 A / 20 mm** a été ajouté
  sur le positif du rail moteur en réponse (voir [parametres.md](parametres.md)).
- **Odométrie faussée.** Les chenilles bloquées ne tournent plus mais les moteurs peuvent
  patiner ou vibrer : les encodeurs cessent de compter alors que le robot « pousse ». Toute
  estimation de pose accumulée pendant un blocage est fausse.

## Impact sur les phases futures

- **Phase 6 (odométrie réelle) :** un blocage pendant un parcours de validation invalide la
  mesure de dérive. Reprendre le test.
- **Phase 10 (SLAM + Nav2) :** les parcours de navigation seront faussés par les blocages —
  la pose estimée dérive brutalement, la carte se désaligne. Le comportement de récupération
  Nav2 (« robot bloqué ? ») devra être réglé et testé explicitement sur cette plateforme, et
  la surconsommation associée surveillée via `surveillance_alimentation`.

## Détection

`surveillance_alimentation` publie le courant du rail moteur sur `/alimentation/moteur`
(`sensor_msgs/BatteryState`, champ `current`). Un courant moteur qui reste élevé (> ~3 A) alors
que les encodeurs ne bougent pas est la signature d'un blocage. Aucune détection automatique
n'est implémentée à ce jour : ce document sert de repère pour l'interprétation manuelle et pour
une éventuelle protection logicielle ultérieure.

## Conduite à tenir

- Ne pas insister sur une consigne moteur quand le robot ne bouge plus : couper la consigne
  (arrêt clavier, `Ctrl+C`, ou `/pico/stop_moteurs`).
- Après un blocage prolongé, vérifier la température du câblage de masse du rail moteur et
  l'état du fusible avant de repartir.
- En phase de navigation, considérer tout écart d'odométrie soudain comme un blocage possible.
