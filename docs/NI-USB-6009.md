# NI USB-6009 — câblage et acquisition du TP

Le câblage ci-dessous est **confirmé par l'utilisateur le 15 octobre 2026**, sans inspection du
montage. Les caractéristiques du matériel ont été recoupées avec les sources NI
en fin de document. La configuration historique du Datalogger reste à vérifier.

## Voie, débit et brochage

La voie visée est **`Dev1/ai1`**, avec une acquisition Python via le pilote
**NI-DAQmx** et le paquet **`nidaqmx`**, à **4 000 échantillons/s** sur une voie.
`Dev1` est le nom du périphérique à vérifier dans NI MAX ou dans l'application.
Le paquet Python ne remplace pas le pilote système NI-DAQmx.

Pour le **USB-6009 standard à borniers à vis** (pas la version OEM) :

| Borne physique | Nom en mode simple | Rôle pour la voie différentielle `ai1` |
| --- | --- | --- |
| 5 | AI1 | AI1+, entrée positive |
| 6 | AI5 | AI1−, entrée négative |
| 7 | GND | Masse |

En différentiel, `Dev1/ai1` utilise automatiquement la paire AI1/AI5 ; ne pas
ajouter `Dev1/ai5` comme seconde voie indépendante pour cette mesure.

## Câblage actuel confirmé

```text
Signal +  ───────── borne 5 : AI1 (AI1+)
Signal −  ───────── borne 7 : GND
                         │
                    cavalier 6–7
                         │
                    borne 6 : AI5 (AI1−)
```

Avec ce cavalier, AI5 est reliée à GND. En mode différentiel, la tension mesurée
est donc `V(AI1) − V(AI5) = V(AI1) − V(GND)`. En RSE, la voie AI1 est mesurée
directement par rapport à GND ; le cavalier ne change pas sa référence.
Ce montage est compatible avec les deux modes et **ne prouve pas que l'ancien
Datalogger utilisait le différentiel**. La référence négative reste reliée à la
masse, même avec une configuration logicielle différentielle.

## Deux configurations à distinguer

| Réglage | Différentiel | RSE |
| --- | --- | --- |
| Voie DAQmx | `Dev1/ai1` | `Dev1/ai1` |
| `TerminalConfiguration` | `DIFFERENTIAL` | `RSE` |
| Référence négative | AI5, borne 6, reliée ici à GND | GND |
| Résolution nominale USB-6009 | 14 bits | 13 bits |
| Gamme considérée pour le TP | −5 à +5 V | −10 à +10 V |
| Débit demandé | 4 000 échantillons/s | 4 000 échantillons/s |

La gamme ±5 V est disponible en différentiel ; le mode RSE du USB-6009 dispose
de la gamme ±10 V. Le choix différentiel ±5 V convient si le signal reste dans
cette gamme. La résolution nominale ne garantit pas une précision effective de
14 bits : bruit, précision absolue et chaîne analogique interviennent aussi.
Chaque entrée doit respecter la tension de fonctionnement ±10 V par rapport à
GND, même lorsqu'une gamme différentielle plus grande est disponible.

## Exemple Python pour un essai différentiel

Exemple autonome à utiliser après vérification du montage et de la gamme du
signal ; il ne constitue pas une validation matérielle ni une modification des
réglages du logiciel du projet.

```python
import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan(
        "Dev1/ai1",
        terminal_config=TerminalConfiguration.DIFF,
        min_val=-5.0,
        max_val=5.0,
    )
    task.timing.cfg_samp_clk_timing(
        rate=4000.0,
        sample_mode=AcquisitionType.CONTINUOUS,
        samps_per_chan=4000,
    )
    task.start()
    print("Fréquence configurée :", task.timing.samp_clk_rate, "éch/s")
    try:
        while True:
            tensions = task.read(number_of_samples_per_channel=200, timeout=1.0)
            # Traiter ou enregistrer ce bloc de tensions en volts.
    except KeyboardInterrupt:
        pass
```

Pour un essai RSE, remplacer `DIFF` par `RSE` et les limites par
`min_val=-10.0`, `max_val=10.0`.

## Application au projet et vérification historique

Le worker de `radio_datalogger/daq.py` configure déjà explicitement la voie,
le mode, la gamme et l'horloge d'acquisition continue via `nidaqmx` ; il récupère
aussi la fréquence effective du pilote. L'interface mémorise les réglages.
À défaut de réglages enregistrés, `main_window.py` initialise la fréquence à
1 000 éch/s, le mode à `DIFFERENTIAL` et la gamme à ±10 V. L'ancien mode
mémorisé `DEFAULT` est remplacé par `DIFFERENTIAL` au lancement ; un choix
explicite mémorisé (RSE, etc.) est conservé. Seuls les modes annoncés par le
pilote pour la voie sélectionnée sont proposés. Le worker transmet explicitement
`TerminalConfiguration.DIFF` à NI-DAQmx pour la seule voie `ai1`.
**4 000 éch/s et la gamme ±5 V restent à sélectionner selon le signal**.

Avant de figer les réglages du TP :

1. Relever dans l'ancien Datalogger, sa tâche NI MAX, ses sources ou ses fichiers
   de configuration la voie, le mode de connexion, la gamme et le débit.
2. Le câblage aux bornes 5, 6, 7 et le cavalier 6–7 sont confirmés par
   l'utilisateur. Vérifier l'amplitude réelle du signal avant de réduire la gamme.
3. Sélectionner explicitement le mode retenu dans l'application : `DEFAULT`
   laisse le pilote choisir et ne documente pas le choix historique.
4. Valider une acquisition sur matériel à 4 000 éch/s avec une tension connue ;
   conserver les réglages, la version du pilote, la fréquence effective et les CSV.

Le différentiel est désormais le mode par défaut demandé pour le TP ; la gamme
±5 V reste une possibilité technique et son utilisation historique reste une
hypothèse. Aucun essai sur un USB-6009 réel n'a été effectué pour
cette transmission documentaire.

## Sources NI

- [NI USB-6008/6009 User Guide](https://download.ni.com/support/manuals/371303n.pdf),
  figure 4, brochage du bornier standard et sections sur les mesures analogiques.
- [USB-6009 Specifications](https://www.ni.com/docs/en-US/bundle/usb-6009-specs/page/specs.html),
  section Analog Input : résolutions, gammes, limites et débit maximal agrégé de
  48 kéch/s.
