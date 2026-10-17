# Dossier de révision — parcours local complet

Il s’agit d’une tâche fictive de développement, pas d’une preuve recueillie auprès
d’agriculteurs. Vous comparerez des feuilles papier synthétiques, préparerez des
copies vérifiées, examinerez un résultat non résolu, appliquerez une décision de
doublon explicite et créerez une copie locale pour le conseiller. Il faut la CLI
installée `0.1.0a1` et l’environnement Windows/Python décrit dans le
[guide du pipeline](../../docs/workflows/local-pipeline.md).

## 1. Choisir la tâche et vérifier la transcription

Question : quels achats et quelles réceptions de septembre pour `ENT-001` faut-il
clarifier ? La juridiction de l’activité est `CA-ON` uniquement pour le routage
synthétique ; la période inclusive va du 2026-09-01 au 2026-09-30, en CAD, sur la
base des pièces d’achat. Le destinataire prévu est un conseiller synthétique local.
Cela n’établit aucun soutien opérationnel pour l’Ontario ou une production donnée.

Lisez la [feuille d’achats](../manual/fr/purchases-paper.md) et la
[feuille de réceptions](../manual/fr/receiving-paper.md). Comparez chaque champ au
[CSV des achats](../manual/fr/purchases.csv) et au
[CSV des réceptions](../manual/fr/receiving.csv). A-03 pourrait recopier A-02, une
unité est vide et les réceptions peuvent différer. N’inventez pas de résolution.
Pour une nouvelle tâche, copiez le [modèle vierge](../../templates/fr/manual-entry.csv)
et utilisez les guides de [contexte](../../templates/fr/intake.md) et de
[correspondance](../../templates/fr/mapping.md).

Après comparaison et confirmation de ce périmètre synthétique, préparez les entrées :

```powershell
.venv\Scripts\agent-agriculture.exe --language fr capture --purchase examples\manual\fr\purchases.csv --receiving examples\manual\fr\receiving.csv --output outputs\manual-fr-inputs --task-id manual-fr --enterprise ENT-001 --jurisdiction CA-ON --start 2026-09-01 --end 2026-09-30 --currency CAD --question "Quels enregistrements faut-il clarifier ?" --recipient "Conseiller synthétique local" --current-tool "Feuille papier synthétique vérifiée" --coverage complete --confirm-authority --confirm-mapping --confirm-transcription
```

Les drapeaux consignent des vérifications effectives ; le logiciel ne lit pas le
papier. `prepared_inputs` signifie que copies et configuration existent localement,
pas que les enregistrements concordent. Un dossier de sortie existant est refusé.
Choisissez un nouveau dossier pour répéter la préparation, sans écraser les pièces.

## 2. Examiner le résultat avant une décision de doublon

```powershell
.venv\Scripts\agent-agriculture.exe --language fr reconcile --task outputs\manual-fr-inputs\task.json --manifest outputs\manual-fr-inputs\manifest.json --output outputs\manual-fr-runs
```

La commande affiche le chemin de l’instantané validé. Ouvrez `summary.md` et
`record-review.md`. Les montants sources fournis totalisent 665,00 CAD ; aucun
total d’achats uniques confirmé n’est établi car A-02 et A-03 exigent une révision
d’identité. Les unités inconnues restent visibles. Ne transformez pas cette somme
source en bénéfice ou en total complet de l’exploitation.

## 3. Consigner une décision révisée explicite

Le [fichier de correction](../manual/fr/corrections.json) représente une variante
synthétique confirmant que A-03 recopie A-02. Examinez la référence précédente
exacte, la version, l’horodatage, le pseudonyme du réviseur et le motif avant
application. Cette décision fournie n’autorise pas l’exclusion d’un enregistrement
semblable dans une autre tâche.

```powershell
.venv\Scripts\agent-agriculture.exe --language fr reconcile --task outputs\manual-fr-inputs\task.json --manifest outputs\manual-fr-inputs\manifest.json --corrections examples\manual\fr\corrections.json --output outputs\manual-fr-runs
```

Le nouvel instantané conserve les deux pièces d’origine, inclut 545,00 CAD et exclut
120,00 CAD. Le sous-ensemble comparable à unités confirmées compte 165 kg achetés
et 163 kg reçus. Pour INV-002, l’écart réceptions moins achats est de -2 kg. Les
deux enregistrements d’unité inconnue restent non attribués : le dossier est encore
incomplet. Suivez les lignes et calculs sources ; ces attentes imprimées ne prouvent
rien au sujet d’un autre jeu de données.

## 4. Vérifier et préparer la copie locale pour le conseiller

Utilisez le chemin de l’instantané révisé affiché à l’étape 3 :

```powershell
.venv\Scripts\agent-agriculture.exe --language fr verify "<chemin de l’instantané révisé>"
.venv\Scripts\agent-agriculture.exe --language fr handoff --run "<chemin de l’instantané révisé>" --output outputs\manual-fr-conseiller
```

Lisez les nouveaux fichiers `index.md`, `summary.md`, `record-review.md`,
`calculations.json`, `exceptions.json` et `handoff.json`. La copie est utilisable
sans cet outil. Elle indique question, résultats vérifiés, questions non résolues,
destinataire et pièces d’origine omises. Le JSON normalisé complet, les autorisations
et l’historique des réviseurs restent chez l’agriculteur. Examinez les textes libres
avant partage ; aucune transmission n’est effectuée.

Un rapprochement identique réutilise son instantané. Une modification confirmée
des sources ou corrections en crée un autre. Conservez l’instantané complet vérifié
et les décisions séparées lorsque vous quittez l’outil. Consultez les
[consignes d’export](../../templates/fr/export.md).

## Enregistrements partiels et papier réel

Pour une transcription partielle, utilisez `--coverage partial --omission "Pages
choisies non fournies"` ; utilisez `unknown` si l’exhaustivité est inconnue. Cet
assistant de préparation applique une même déclaration aux deux sources. Si leurs
couvertures diffèrent, confirmez chaque source séparément dans le manifeste préparé
avant le rapprochement. Conservez la cohérence des originaux, empreintes et périodes.

La [référence d’export partiel](../../tests/fixtures/cases/partial-export/) comporte
date ambiguë, entreprise manquante et lignes omises. Elle produit un dossier
incomplet utile avec une somme fournie de 445,00 CAD, sans total complet de
l’entreprise pour la période. Le [modèle d’exceptions](../../templates/fr/exceptions.md)
consigne les pièces nécessaires. Si le papier est indisponible ou l’extraction
incertaine, conservez un brouillon ou une ligne non résolue plutôt que de prétendre
à une vérification. Le CSV local offre une saisie pour import ultérieur ; l’éditeur
ou l’hôte doit réellement enregistrer le fichier.
