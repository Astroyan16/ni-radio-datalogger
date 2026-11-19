# NI Datalogger 0.1.2

- Interface générique, sans consignes propres à une manipulation radio.
- Plage demandée initiale **0 à 5 V**, avec mode différentiel présélectionné.
- Préférence pour **ai1 si elle accepte le différentiel**, sinon première voie
  disponible. Une voie ou un mode explicitement mémorisés restent prioritaires.
- Les réglages déjà enregistrés, notamment la plage de tension, sont conservés.
- Les nouveaux CSV utilisent la colonne **voltage_v**, dans l'enregistrement
  progressif comme dans l'export complet. Les scripts qui lisaient la colonne
  `interferometer_voltage_v` des versions précédentes doivent être adaptés.

Télécharger et extraire `NI-Radio-Datalogger-0.1.2-windows-x64.zip`, puis lancer
l'exécutable. Le nom des fichiers distribués reste inchangé pour faciliter la
transition. Python n'est pas nécessaire. Pour une acquisition matérielle,
installer séparément le pilote système NI-DAQmx compatible avec le périphérique.

La validation comprend 24 tests logiciels et le contrôle de l'exécutable Windows
en simulation : acquisition, affichage, CSV progressif et complet, arrêt et
redémarrage. L'acquisition sur un périphérique réel reste à qualifier.
