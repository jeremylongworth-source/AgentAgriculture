# Préparer une copie pour le conseiller et garder le contrôle

Vérifiez l’instantané source validé, puis préparez une nouvelle copie locale :

```powershell
.venv\Scripts\agent-agriculture.exe --language fr verify "<chemin de l’instantané>"
.venv\Scripts\agent-agriculture.exe --language fr handoff --run "<chemin de l’instantané>" --output "<nouveau dossier local pour le conseiller>"
```

Lisez `index.md` et `handoff.json` avant tout partage. La copie contient le résumé,
la comparaison des sources et interprétations, les calculs et les exceptions. Son
manifeste indique les empreintes, le destinataire prévu et les omissions. Les CSV
d’origine, le JSON normalisé complet, les autorisations et l’historique des réviseurs
sont omis. Les références restent traçables vers l’instantané complet conservé par
l’agriculteur, mais les pièces d’origine ne font pas partie de cette copie minimale.

Examinez les textes libres et le périmètre pour retirer les renseignements personnels
ou financiers inutiles. Choisissez d’autres pièces uniquement si la question en a
besoin et si l’autorisation de partage les couvre. Ne retirez pas de fichiers d’un
instantané validé ; préparez une copie distincte. Le conseiller peut lire Markdown
et JSON sans cet outil. Le CSV emploie les en-têtes et décimales de la langue choisie ;
les valeurs JSON et les identifiants techniques restent stables.

Ces commandes préparent des fichiers locaux. Elles n’envoient, ne synchronisent,
ne déposent et ne certifient rien, et n’obtiennent aucune approbation du conseiller.
Un dossier partiel reste partiel. Conservez l’instantané et les décisions pour les
corrections, l’export ou le retour aux outils existants.
