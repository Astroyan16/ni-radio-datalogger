# Historique des versions

## 0.1.1 — 2026-11-12

- Mode différentiel présélectionné, y compris à la place de l'ancien réglage
  automatique mémorisé ; les modes explicites enregistrés restent conservés.
- Correction de la détection et de la transmission du différentiel à NI-DAQmx :
  la constante Python est `TerminalConfiguration.DIFF`.
- Câblage du TP confirmé : AI1 borne 5, retour borne 7, cavalier 6–7.
- Tests du mode différentiel, de sa détection et des réglages de l'interface.

## 0.1.0 — 2026-09-07

Première version préparée pour une distribution Windows x64.

### Acquisition et affichage

- Interface Qt en français pour une seule entrée analogique de tension.
- Détection des périphériques NI-DAQmx et présélection de l'entrée `ai1`.
- Configuration de l'entrée, du mode de connexion, de la fréquence et de la
  plage de tension.
- Acquisition continue dans un thread dédié et signal simulé sans matériel.
- Courbe temps réel, fenêtre bornée, échelle verticale automatique et
  statistiques de la fenêtre affichée.
- Conservation des réglages de l'interface entre les lancements.

### Enregistrement

- CSV progressif démarrable et arrêtable pendant l'acquisition.
- Copie temporaire sur disque de la session complète et export CSV après arrêt.
- Métadonnées d'acquisition, index des échantillons, temps écoulé et tension.

### Distribution et vérification

- Métadonnées de version `0.1.0`, dépôt GitHub et documentation en français.
- Construction PyInstaller d'un exécutable Windows x64 sans installation Python.
- Archive portable avec documentation, notices et empreintes SHA-256.
- Environnement de compilation à versions figées et workflow GitHub Windows.
- Recherche des DLL isolée pendant la compilation pour éviter les bibliothèques
  étrangères au projet présentes dans le PATH du poste.
- 14 tests passants sur les modèles, le tampon, les enregistrements et
  l'acquisition : continuité et arrêt de la simulation, configuration NI avec
  interface simulée, fréquence effective et erreurs de module/pilote absent.
- Commande `--smoke-test DOSSIER` pour vérifier le parcours en simulation depuis
  les sources ou l'exécutable. Le contrôle des sources a réussi avec le rendu
  natif Windows et une fenêtre masquée : import de `nidaqmx`, affichage,
  statistiques, CSV progressif, export complet, arrêt et redémarrage.

### Corrections avant distribution

- Fin d'acquisition déclenchée par `QThread.finished`, pour attendre la fin
  effective du thread avant de libérer le worker et de permettre un redémarrage.

### Limites connues

- Validation sur un véritable NI USB-6009 et sur Windows 10 encore à effectuer.
- Pilote système NI-DAQmx nécessaire pour le matériel et installé séparément.
- Session temporaire supprimée à la nouvelle acquisition ou à la fermeture.
- Horodatage UTC issu du système, sans synchronisation matérielle.
- Exécutable non signé ; essais prolongés et déconnexion USB à valider.
