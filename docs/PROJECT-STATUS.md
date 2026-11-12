# État du projet — préparation de la version 0.1.0

Évaluation du 7 septembre 2026 à partir des sources, des tests et du contrôle
de l'application en simulation pendant la préparation de la distribution.

Le projet dispose d'un parcours logiciel cohérent : sélectionner une source,
acquérir, afficher, enregistrer et exporter. Il peut être présenté et essayé en
simulation. La version 0.1.0 vise à rendre ce socle installable et vérifiable
sous Windows ; elle ne constitue pas encore une qualification de la chaîne de
mesure avec l'USB-6009.

## Éléments déjà implémentés

| Domaine | État observé | Limite de la conclusion |
| --- | --- | --- |
| Interface | Application PySide6/pyqtgraph en français, réglages conservés et commandes d'acquisition/CSV ; parcours simulé vérifié dans le binaire | Les conditions matérielles et acquisitions prolongées restent à qualifier |
| Acquisition NI | Découverte des périphériques, configuration de voie/tension/fréquence, lecture continue dans un `QThread` ; configuration et fréquence effective testées avec une interface NI simulée | Pas de validation sur un vrai USB-6009 |
| Simulation | Génération d'un signal avec bruit, émission des échantillons par le même worker que le parcours matériel | Ne vérifie ni pilote, ni câblage, ni fidélité des mesures |
| Affichage | Tampon circulaire, conservation des points récents, redimensionnement, courbe et statistiques | Une mémoire d'affichage bornée ne garantit pas le débit global lors d'une acquisition longue |
| CSV progressif | Métadonnées, indices et tensions écrits au fil de l'eau, début/arrêt indépendant de l'acquisition | Les performances disque et les erreurs de stockage restent à éprouver en conditions réelles |
| Session complète | Copie binaire temporaire sur disque, export CSV après arrêt | Copie supprimée à la nouvelle acquisition et à la fermeture ; pas de reprise de session |
| Configuration | Validation de la voie, de la fréquence et de la plage de tension | Les contraintes électriques et de câblage relèvent aussi du matériel |

## Vérifications et distribution

Mise à jour du 15 octobre 2026 : **20 tests passants** après ajout des contrôles
du différentiel (détection NI, configuration du worker et réglages de l'interface).
Le mode par défaut est désormais différentiel, avec migration de l'ancien
`Default` mémorisé ; les modes explicites restent conservés. La constante du
pilote utilisée est `TerminalConfiguration.DIFF`. Le câblage aux bornes 5, 6, 7
avec cavalier 6–7 a été confirmé par l'utilisateur. Ces changements sont inclus dans la version 0.1.1.

Lors de la préparation 0.1.0, la suite comportait **14 tests passants** : quatre sur le tampon circulaire,
quatre sur la configuration, deux sur les enregistrements et quatre sur
l'acquisition. Les tests d'acquisition vérifient la continuité et l'arrêt de la
simulation, la configuration NI et l'utilisation de la fréquence effective avec
une interface simulée, l'erreur en l'absence du module NI et la découverte en cas
d'erreur du pilote. Ces contrôles ne couvrent pas un périphérique réel ni les
performances prolongées.

Le contrôle `--smoke-test DOSSIER` des **sources et du binaire a réussi sous Windows 11 x64**,
avec le rendu Qt natif Windows et une fenêtre masquée. Il a vérifié l'import et
les métadonnées de `nidaqmx`, la simulation, le tampon borné, la courbe, les
statistiques, l'arrêt et le redémarrage. Le CSV progressif de 300 points a été
vérifié comme un sous-ensemble exact de l'export complet de 700 points. Un
rapport JSON et une image PNG accompagnent ces CSV. Ce contrôle n'a accédé à
aucun matériel.

La fin d'acquisition utilise désormais `QThread.finished`, afin que le nettoyage
et la possibilité de redémarrer interviennent après la fin effective du thread.

La préparation 0.1.0 ajoute une compilation Windows x64 avec Python 3.12 et
PyInstaller, un environnement de compilation à versions figées, une archive
portable documentée, les notices des dépendances et des empreintes SHA-256.
Le dépôt public est
[Astroyan16/ni-radio-datalogger](https://github.com/Astroyan16/ni-radio-datalogger).

L'exécutable autonome a passé le même parcours, avec `frozen: true` dans le
rapport de contrôle. L'archive portable contient le programme, la documentation
et les notices ; des empreintes SHA-256 accompagnent les fichiers distribués.
La compilation isole la recherche des DLL après correction d'une inclusion
accidentelle de bibliothèques externes au projet. Le workflow GitHub Windows
exécute également les tests, construit et contrôle le binaire.

## Travaux restant à valider

Une [note NI USB-6009](NI-USB-6009.md), ajoutée le 15 octobre 2026, consigne
le câblage confirmé (AI1 borne 5, retour borne 7, cavalier 6–7), la cible
`Dev1/ai1` à 4 000 éch/s et les possibilités différentiel 14 bits ±5 V ou
RSE 13 bits ±10 V. **Le mode et la gamme de l'ancien Datalogger restent à
vérifier** ; le câblage seul ne permet pas de les déduire.

1. **Étendre la validation Windows** : les 14 tests et les contrôles des sources
   et de l'exécutable ont réussi sous Windows 11 x64. Tester également un poste
   utilisateur vierge et Windows 10, qui ne sont pas validés à ce stade.
2. **Qualifier une acquisition réelle** : USB-6009, version de NI-DAQmx consignée,
   voie et câblage identifiés, signal de tension connu, fréquence effective et
   comparaison des données exportées à la référence injectée.
3. **Éprouver les conditions de TP** : acquisition prolongée au débit utilisé,
   réactivité de l'interface, espace disque, arrêt puis reprise, déconnexion USB
   et comportement lors d'une erreur de stockage.
4. **Définir les exigences scientifiques** : précision attendue, référence de
   temps, synchronisation de l'ordinateur et chaîne de calibration. L'UTC
   actuellement inscrit dans les CSV provient du système ; aucune référence
   matérielle absolue n'est acquise.

La priorité après la distribution 0.1.0 est une séance de validation sur le
montage réel, avec conservation des paramètres, versions et mesures de
référence. Cela permettra de distinguer les corrections nécessaires des
fonctionnalités supplémentaires à envisager.
