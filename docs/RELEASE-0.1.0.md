# NI Radio Datalogger 0.1.0

Première version pour Windows x64 de l'application d'acquisition analogique
destinée aux TP de radioastronomie. Elle visualise et enregistre la sortie
basse fréquence d'une électronique d'interférométrie sur une seule voie NI,
avec une source Simulation pour les essais sans matériel.

## Télécharger et lancer

Télécharger `NI-Radio-Datalogger-0.1.0-windows-x64.zip`, extraire l'archive dans un
dossier accessible en écriture, puis lancer
`NI-Radio-Datalogger-0.1.0-windows-x64.exe`. L'archive contient aussi la
documentation et les notices des dépendances. L'exécutable est également
fourni séparément.

Python n'est pas requis. Pour utiliser un périphérique NI, installer séparément
le pilote système NI-DAQmx compatible avec ce matériel et Windows. La Simulation
ne nécessite ni ce pilote ni un périphérique.

Pour vérifier un téléchargement dans PowerShell, comparer le résultat à la
ligne correspondante de `SHA256SUMS.txt` :

```powershell
Get-FileHash .\NI-Radio-Datalogger-0.1.0-windows-x64.zip -Algorithm SHA256
```

## Contenu de cette version

- Détection NI-DAQmx, choix d'une entrée analogique et présélection de `ai1`.
- Réglage de la fréquence, de la plage de tension et du mode de connexion.
- Acquisition continue, courbe temps réel, échelle verticale automatique et
  statistiques de la fenêtre affichée.
- Enregistrement CSV pendant l'acquisition et export de la session complète
  après l'arrêt.
- Simulation intégrée et mémorisation des réglages de l'interface.
- Distribution Windows x64, dépendances de compilation figées, notices des
  composants et empreintes SHA-256.

## Validation

**14 tests passants** couvrent le tampon d'affichage, la configuration, les CSV,
la simulation, l'arrêt et les échanges avec une interface NI simulée. La
préparation utilise Windows 11 x64 et Python 3.12 x64.

Le contrôle `--smoke-test DOSSIER` des **sources et de l'exécutable a réussi**, avec le rendu Qt
natif Windows et une fenêtre masquée. Il a vérifié l'import de `nidaqmx`, la
simulation, le tampon et les statistiques, les CSV, l'arrêt et le redémarrage.
Les 300 points du CSV progressif correspondent à ceux de l'export complet de
700 points. Un rapport JSON et une image PNG ont été produits sans accès au
matériel.

La construction PyInstaller et le contrôle du binaire autonome ont réussi sous
Windows 11 x64. L'exécutable fait environ 64 Mo. La compilation isole les chemins
de recherche des DLL pour éviter d'embarquer les bibliothèques d'autres logiciels.
Le workflow GitHub reproduit les tests, la compilation et le contrôle du binaire.

Le fonctionnement avec un véritable USB-6009, les acquisitions prolongées, la
déconnexion USB en cours de mesure et Windows 10 ne sont pas encore validés.

## Limites à connaître

- **Exporter avant une nouvelle acquisition ou la fermeture** : la copie
  temporaire de la session est alors supprimée. Un CSV déjà enregistré reste
  conservé à l'emplacement choisi.
- La fenêtre affichée est bornée, mais la session complète consomme de l'espace
  disque au fil de l'acquisition.
- L'heure UTC de départ est celle du système et reste approximative. Les temps
  relatifs sont calculés à partir de l'index et de la fréquence effective ; aucun
  horodatage matériel absolu n'est fourni.
- L'exécutable n'est pas signé numériquement ; Windows peut afficher une demande
  de confirmation de l'éditeur au premier lancement.
- L'application traite une tension basse fréquence déjà préparée par
  l'électronique externe, sans acquisition RF directe ni corrélation de deux
  voies.

Les sources, instructions de compilation et limites de validation sont
disponibles dans le [dépôt public](https://github.com/Astroyan16/ni-radio-datalogger).
