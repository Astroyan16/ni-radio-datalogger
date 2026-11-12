# NI Radio Datalogger 0.1.1

Le mode **Différentiel (DIFF)** est présélectionné lorsque la voie le permet.
L'ancien réglage automatique `Default` est remplacé au lancement ; un choix
explicite enregistré, comme RSE, est conservé. La fréquence et la plage de
tension mémorisées sont conservées.

La détection du mode différentiel et la configuration de l'acquisition utilisent
désormais le nom `DIFF` attendu par NI-DAQmx. Pour le TP sur `ai1`, le câblage
confirmé est : **signal + borne 5, retour borne 7 et cavalier 6–7**.
Voir la [note sur l'USB-6009](NI-USB-6009.md) pour les réglages et le brochage.

La distribution portable Windows x64 ne nécessite pas Python. Pour une
acquisition réelle, le pilote système **NI-DAQmx** doit être installé séparément.
Les tests logiciels et le contrôle en simulation ne valident pas une acquisition
sur le matériel réel.
