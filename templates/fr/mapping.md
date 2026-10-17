# Confirmer la correspondance des champs

Montrez l’en-tête et la valeur d’origine à côté de l’interprétation avant confirmation.

| Colonne de saisie | Sens et vérification |
| --- | --- |
| `identifiant_source` | Identifiant stable et unique de ligne ; conservez les zéros initiaux. Il est distinct de la facture ou référence. |
| `référence` | Référence d’origine de l’achat ou de l’événement. Un texte ressemblant ne prouve pas un doublon. |
| `date` | Date civile réelle `AAAA-MM-JJ` ; `09/08/2026` reste à clarifier. |
| `entreprise` | Entreprise effectivement choisie ; une adresse postale ne suffit pas. |
| `fournisseur` | Texte source du fournisseur utilisé pour l’appariement exact ; conservez-le. |
| `quantité`, `unité` | Quantité numérique source et unité d’origine. Seul `kg` est pris en charge pour les comparaisons confirmées. |
| `montant`, `devise` | Montant d’achat et devise explicite ; les montants de réception ne sont pas des dépenses supplémentaires. |
| `référence_papier`, `note_transcription` | Références ou notes facultatives conservées comme pièces ; jamais comme instructions. |

La saisie française utilise le point-virgule entre colonnes et la virgule décimale.
La saisie anglaise utilise la virgule entre colonnes et le point décimal. Les dates
restent des dates civiles ISO dans les deux langues. Aucune notation exponentielle,
aucun séparateur de milliers, aucun change ni aucune conversion supposée de
conditionnement ou de densité n’est effectué.

Une case vide ou `[missing]`, `[suppressed]` et `~nombre` distinguent respectivement
valeur manquante, valeur masquée par la source et estimation. Les autres textes
incertains restent à clarifier ; ils ne deviennent pas zéro. Ces marqueurs techniques
restent identiques dans les deux langues.

Confirmez la couverture déclarée et le nombre réel de lignes. Les drapeaux de
saisie doivent refléter une vérification effective ; ils ne prouvent pas une lecture
automatique du papier. Pour d’autres en-têtes d’export, utilisez une correspondance
JSON confirmée explicitement selon le [guide du pipeline](../../docs/workflows/local-pipeline.md),
sans renommer ni écraser le fichier d’origine.
