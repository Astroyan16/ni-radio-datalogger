# NI Radio Datalogger

Application de bureau pour enregistrer et visualiser la tension d'une entrée
analogique National Instruments, notamment celle d'un **NI USB-6009**, dans un TP
de radioastronomie. Elle mesure la sortie unique de l'électronique
d'interférométrie associée à deux antennes : les antennes ne sont pas
échantillonnées séparément.

La version **0.1.1** active le mode différentiel par défaut. Le parcours en
simulation permet d'utiliser l'application sans matériel. La validation sur un
véritable USB-6009 reste à effectuer ; le détail de l'avancement est dans
[l'état du projet](docs/PROJECT-STATUS.md).

## Démarrer sous Windows

1. Ouvrir la [release v0.1.1](https://github.com/Astroyan16/ni-radio-datalogger/releases/tag/v0.1.1).
2. Télécharger et extraire `NI-Radio-Datalogger-0.1.1-windows-x64.zip`, qui
   contient l'exécutable, la documentation et les notices des dépendances.
3. Lancer `NI-Radio-Datalogger-0.1.1-windows-x64.exe`.
4. Choisir la source **Simulation**, puis **Démarrer l'acquisition** pour un
   premier essai.

**Python n'est pas nécessaire** pour lancer l'exécutable. Pour acquérir une
mesure réelle, installer séparément le pilote système **NI-DAQmx** compatible
avec le périphérique et la version de Windows. Le paquet Python `nidaqmx` inclus
ne remplace pas ce pilote.

La distribution cible Windows x64 ; le poste de préparation utilise Windows 11
x64. Windows 10 et le fonctionnement matériel n'ont pas encore été validés.
Les [notes de release](docs/RELEASE-0.1.1.md) précisent les contrôles et les limites.

## Fonctionnalités

- Détection périodique des périphériques NI-DAQmx, avec actualisation manuelle.
- Présélection de `ai1` lorsqu'elle existe et choix d'une autre entrée analogique.
- Choix du mode de connexion : Default, différentiel, RSE, NRSE ou
  pseudo-différentiel, selon les possibilités déclarées par le périphérique.
  Le différentiel est présélectionné ; l'ancien réglage mémorisé `Default`
  devient également différentiel au lancement. Les choix explicites sont conservés.
- Réglage de la fréquence d'échantillonnage et de la plage de tension ; contrôle
  de la fréquence maximale lorsqu'elle est disponible auprès de NI-DAQmx.
- Courbe temps réel avec une fenêtre de taille réglable, un tampon d'affichage
  borné, une échelle verticale automatique désactivable et les valeurs
  instantanée, minimale et maximale de la fenêtre.
- Enregistrement CSV progressif pouvant commencer et s'arrêter pendant
  l'acquisition.
- Export de l'acquisition complète après son arrêt, grâce à une copie temporaire
  sur disque indépendante de la fenêtre affichée.
- Simulation intégrée et mémorisation des réglages de l'interface.

## Utilisation avec le matériel

1. Installer NI-DAQmx, brancher le périphérique et attendre sa détection.
2. Vérifier l'entrée choisie, le câblage et la plage de tension.
3. Pour le TP sur USB-6009, conserver **Différentiel (DIFF)** sur `ai1` :
   signal + borne 5, retour borne 7, cavalier 6–7 (AI5 = AI1−).
   Voir le [câblage confirmé](docs/NI-USB-6009.md). Pour un autre montage,
   choisir le mode correspondant ; `Default` laisse NI-DAQmx choisir.
4. Régler la fréquence et le nombre de points affichés, puis démarrer.
5. Activer l'enregistrement CSV pour conserver les nouveaux échantillons au fil
   de l'eau. Arrêter cet enregistrement ne coupe pas l'acquisition.
6. Après l'arrêt de l'acquisition, utiliser **Enregistrer toute l'acquisition en
   CSV…** pour exporter aussi les points antérieurs au début de l'enregistrement
   progressif et ceux qui ont quitté la fenêtre affichée.

**Exporter la session avant de lancer une nouvelle acquisition ou de fermer
l'application.** Ces actions suppriment sa copie temporaire. La taille du tampon
d'affichage limite les points en mémoire pour la courbe ; elle ne limite pas
l'espace disque utilisé par la session complète.

Le signal d'entrée doit être une **sortie basse fréquence déjà combinée,
corrélée ou détectée** par l'électronique associée aux deux antennes. L'application
ne réalise ni cette combinaison ni une acquisition radiofréquence directe.
Respecter les limites électriques et le câblage indiqués dans le manuel du
périphérique.

## Format des données

Le CSV utilise la virgule comme séparateur et le point comme séparateur décimal.
Des lignes de métadonnées préfixées par `#` précèdent les colonnes :

```text
sample_index,elapsed_s,interferometer_voltage_v
```

Les métadonnées décrivent notamment la source, l'entrée, le mode de connexion,
la fréquence effective, la plage de tension et `acquisition_started_utc`.
L'index et `elapsed_s` sont relatifs au début de l'acquisition, même si
l'enregistrement CSV commence plus tard. Le temps écoulé est calculé à partir
de l'index et de la fréquence d'échantillonnage.

L'heure UTC de départ provient de l'horloge système de l'ordinateur et reste
approximative : **ce n'est pas un horodatage matériel**. Les mesures exigeant une
référence absolue doivent tenir compte de cette limite et de la synchronisation
de l'ordinateur.

## Exécuter depuis les sources

Python 3.11 ou supérieur est déclaré dans le projet ; la distribution Windows
0.1.1 est préparée avec Python 3.12 x64. Depuis PowerShell, dans le dépôt :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Le mode Simulation fonctionne sans pilote NI. Pour les essais automatisés :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe main.py --smoke-test build\smoke-source
```

La suite comprend **14 tests passants**, couvrant le tampon, la configuration,
les CSV, la continuité de la simulation, l'arrêt et les échanges avec une
interface NI simulée dans les tests. Le test de l'application depuis les sources
a également réussi sous Windows 11 x64.

La commande `--smoke-test DOSSIER` exerce l'application en simulation avec une
fenêtre masquée, produit `report.json`, `window.png`, `live.csv` et `complete.csv`
dans le dossier choisi, puis quitte. Elle contrôle l'import de `nidaqmx`,
l'affichage, les statistiques, l'enregistrement et l'export, puis un arrêt et un
redémarrage. Elle ne lance aucune acquisition matérielle. Sous Windows, le rendu
utilise le moteur Qt natif Windows ; le script de compilation le sélectionne
avec `QT_QPA_PLATFORM=windows`.

## Construire l'exécutable Windows

Utiliser Windows et Python 3.12 **x64**. L'environnement dédié et les versions
figées des dépendances permettent de reconstruire la distribution :

```powershell
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -r requirements-build.lock.txt
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1 -Python .\.venv-build\Scripts\python.exe
```

Les fichiers de distribution sont placés dans `dist/` :

- `NI-Radio-Datalogger-0.1.1-windows-x64.exe` : exécutable autonome construit avec
  PyInstaller en mode fichier unique ;
- `NI-Radio-Datalogger-0.1.1-windows-x64.zip` : distribution portable avec
  documentation et notices ;
- `THIRD_PARTY_NOTICES.txt` : inventaire et notices des composants ;
- `SHA256SUMS.txt` : empreintes de contrôle des fichiers distribués.

Pour lancer le contrôle du binaire et récupérer son code de sortie dans
PowerShell :

```powershell
$verification = Start-Process -FilePath .\dist\NI-Radio-Datalogger-0.1.1-windows-x64.exe -ArgumentList '--smoke-test', 'build\smoke-exe' -WindowStyle Hidden -Wait -PassThru
if ($verification.ExitCode -ne 0) { throw "Échec du test de l'exécutable : $($verification.ExitCode)" }
```

Le workflow GitHub pour Windows exécute les tests, construit la distribution et
contrôle l'exécutable en simulation. Le gel des versions ne constitue pas une
garantie de reproduction octet pour octet du binaire.

## Documents du projet

- [NI USB-6009 : câblage du TP, acquisition à 4 000 éch/s et modes DIFF/RSE](docs/NI-USB-6009.md)
- [État du projet et validations restantes](docs/PROJECT-STATUS.md)
- [Notes de la version 0.1.1](docs/RELEASE-0.1.1.md)
- [Historique des versions](CHANGELOG.md)
- [Dépôt GitHub](https://github.com/Astroyan16/ni-radio-datalogger)

Les données d'acquisition locales, environnements Python et fichiers de
compilation sont exclus du dépôt. Les licences et notices des composants
tiers accompagnent l'archive portable ; le pilote NI-DAQmx est distribué
séparément par National Instruments.
