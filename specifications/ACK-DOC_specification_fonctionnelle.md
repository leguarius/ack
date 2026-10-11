# ACK-DOC
## Spécification fonctionnelle et technique
**Version  :** 1.0
**Plateforme cible  :** Debian 13
**Langage  :** Python 3

## 1. Objet

Le projet ACK-DOC a pour objet de développer une application en ligne de commande permettant :

## 1.	de parcourir une arborescence contenant des documents PDF ;

## 2.	de contrôler la présence et la conformité de balises spécifiques dans chacun de ces documents ;

## 3.	d'extraire les informations contenues dans ces balises ;

## 4.	de rapprocher les documents d'un modèle rédigé au format Markdown ;

## 5.	de générer un document de synthèse au format Markdown ;

## 6.	de générer à partir de ce document un document final au format PDF ;

## 7.	de produire un journal d'exécution au format JSON.

L'application ne comporte aucune interface graphique.

## 2. Documents source

### 2.1 Format

Les documents source sont exclusivement des fichiers au format PDF.
Les fichiers PDF doivent comporter une couche texte exploitable. L'application n'effectue aucune reconnaissance optique de caractères (OCR).
Les balises sont recherchées dans le texte extrait du PDF et non en fonction de leur position visuelle dans le document.
Les fichiers autres que PDF présents dans l'arborescence d'entrée sont ignorés et ne constituent pas des erreurs.
Un PDF corrompu, illisible ou dépourvu de couche texte exploitable constitue une non-conformité bloquante de la source et entraîne le code retour 1. Une panne du moteur d'extraction ou de l'application constitue une erreur technique et entraîne le code retour 2.
Les PDF sont supposés ne pas être protégés contre la lecture.

## 3. Organisation des fichiers

Tout chemin relatif fourni en argument (`--input`, `--template`, `--output` ou `--journal`) est résolu depuis le répertoire courant au lancement de la commande.
Les documents source sont placés dans le répertoire spécifié par l'argument --input ou dans l'un de ses sous-répertoires.
L'application parcourt récursivement toute l'arborescence descendante de ce répertoire.
Le modèle Markdown est fourni séparément par l'argument --template.
Les liens insérés dans le document de synthèse vers les documents PDF source utilisent des chemins relatifs calculés depuis le répertoire du Markdown généré, afin de préserver la portabilité de l'ensemble documentaire. Les chemins source consignés dans le journal sont relatifs à la racine --input.
Si le répertoire --input existe et est accessible, mais ne contient aucun PDF, la validation échoue avec le code retour 1.

## 4. Interface en ligne de commande

L'application est appelée depuis une ligne de commande.
La commande accepte les arguments suivants :
`--input`
Chemin relatif du répertoire racine contenant les documents PDF à analyser. Tous ses sous-répertoires sont parcourus récursivement.
`--template`
Chemin relatif et nom du fichier modèle au format Markdown (.md).
`--output`
Chemin relatif et nom du fichier PDF final à générer.
`--journal`
Chemin relatif et nom du fichier journal JSON à générer.
Exemple :
```bash
ack-doc --input ./documents --template ./template.md --output ./resultats/ack-doc.pdf --journal ./resultats/ack-doc.json
```
Le document Markdown généré porte automatiquement le même nom et est enregistré au même emplacement que le PDF spécifié avec --output, seule son extension étant remplacée par .md.
Ainsi :
--output ./resultats/ack-doc.pdf
entraîne, en cas de succès, la création de :
./resultats/ack-doc.pdf
./resultats/ack-doc.md

## 5. Balises des documents source

### 5.1 Principe général

Chaque document PDF source doit contenir exactement une occurrence de chacune des trois balises suivantes :
- ANACK
- ORNUM
- EXSUM
L'ordre dans lequel ces trois balises apparaissent dans le PDF n'a pas d'importance.
Chaque balise est constituée :
- d'une balise d'ouverture ;
- d'un contenu ;
- d'une balise de fermeture.
Syntaxe générale :
[[NOM_BALISE]]contenu[[/NOM_BALISE]]
Les noms des balises sont sensibles à la casse.
Par exemple, [[anack]], [[Anack]] ou [[ANAck]] ne sont pas équivalents à [[ANACK]].
La présence de plusieurs occurrences d'une même balise dans un document constitue une erreur bloquante.
Les espaces périphériques situés entre les balises et la valeur sont supprimés avant validation du contenu. Cette suppression porte exclusivement sur les caractères ASCII espace (`U+0020`), tabulation (`U+0009`), saut de ligne (`U+000A`) et retour chariot (`U+000D`). Les espaces Unicode et les autres caractères ne sont ni retirés ni normalisés.

### 5.2 Tolérance aux altérations de l'extraction

L'extraction PDF peut séparer les caractères d'un marqueur par des espaces ou des sauts de ligne ASCII, par exemple si le marqueur est fragmenté dans la couche texte. Pour reconnaître les marqueurs, l'application ignore ces caractères uniquement lorsqu'ils se trouvent à l'intérieur du marqueur et sur une même page. Elle ne les supprime pas dans le contenu des balises et ne fusionne jamais le texte de pages différentes pour reconstituer un marqueur.
Une balise mal formée qui n'est pas reconnue par cette règle est signalée comme `MALFORMED_TAG`; la balise obligatoire correspondante est également signalée comme `MISSING_TAG` lorsqu'elle n'a pas été reconnue. Une balise dont l'ouverture ou la fermeture se trouve sur une autre page est une erreur bloquante.

## 6. Balise ANACK

### 6.1 Fonction

ANACK (Analytical Classification Key) identifie la clé analytique à laquelle appartient le document.

### 6.2 Syntaxe

Exemple :
[[ANACK]]ACK0130[[/ANACK]]
Après suppression des espaces périphériques, le contenu doit respecter strictement la structure :
ACK + 4 chiffres
Exemples valides :
ACK0001
ACK0130
ACK9999
Exemples invalides :
ACK130
ACK01300
ack0130
ABC0130
0130
La casse doit être strictement respectée.
Ainsi :
[[ANACK]] ACK0130 [[/ANACK]]
est accepté et produit la valeur :
ACK0130
La normalisation ne modifie jamais la casse, ne convertit pas les chiffres Unicode en chiffres ASCII et n'applique aucune normalisation Unicode. Une valeur ANACK ne contenant pas exactement `ACK` suivi de quatre chiffres ASCII est invalide.

## 7. Balise ORNUM

### 7.1 Fonction

ORNUM (Order Number) détermine l'ordre d'insertion des documents partageant la même valeur ANACK.

### 7.2 Syntaxe

Exemple :
[[ORNUM]]2[[/ORNUM]]
Après suppression des espaces périphériques, le contenu doit être constitué d'un chiffre unique, compris entre 0 et 9.
Exemples valides :
0
1
5
9
Exemples invalides :
10
01
A
2A
Ainsi :
[[ORNUM]] 2 [[/ORNUM]]
est accepté et produit la valeur :
2
La valeur `0` est valide et précède `1` dans l'ordre numérique croissant.

### 7.3 Unicité

Pour une même valeur ANACK, chaque valeur ORNUM doit être unique.
Deux documents possédant la même combinaison ANACK + ORNUM constituent une erreur bloquante.
Exemple interdit :
document_A.pdf : ACK0130 / ORNUM 2
document_B.pdf : ACK0130 / ORNUM 2
La même valeur ORNUM peut en revanche être utilisée avec deux valeurs ANACK différentes.
Exemple autorisé :
document_A.pdf : ACK0130 / ORNUM 2
document_B.pdf : ACK0140 / ORNUM 2

## 8. Balise EXSUM

### 8.1 Fonction

EXSUM (Executive Summary) contient le résumé du document devant être inséré dans le document de synthèse.

### 8.2 Syntaxe

Exemple :
[[EXSUM]]This is the summary.[[/EXSUM]]
Le contenu peut comporter :
- des lettres ;
- des chiffres ;
- des espaces ;
- des signes de ponctuation ;
- des sauts de ligne.
Après suppression des espaces périphériques, le contenu :
- ne doit pas être vide ;
- ne doit pas commencer par le préfixe littéral majuscule `ACK` (la règle est sensible à la casse) ;
- ne doit pas commencer par un chiffre ASCII (`0` à `9`).
Les lettres et signes de ponctuation Unicode sont admis dans le reste du résumé. La validation ne convertit pas la casse et ne normalise pas les caractères Unicode. Les caractères d'espacement Unicode et les autres caractères de contrôle ne sont pas retirés silencieusement et rendent le résumé invalide. Les espaces périphériques ASCII sont retirés selon la liste définie au §5.1.
Exemples valides :
This is the summary.
Version 2 of the process.
Exemples invalides :
ACK document summary
2 documents were reviewed.

### 8.3 Sauts de ligne

Un ou plusieurs sauts de ligne à l'intérieur du contenu EXSUM sont autorisés.
Ils ne constituent pas une erreur de validation.
Ils doivent être conservés lors de l'extraction puis restitués dans le document Markdown et dans le document PDF final.
Un EXSUM dont le contenu s'étend sur plusieurs pages est une erreur bloquante `EXSUM_CROSSES_PAGE`. Les sauts de page ne sont pas assimilés à de simples sauts de ligne; les résumés doivent tenir sur une seule page source.

## 9. Contrôle de structure des balises

L'application contrôle notamment les anomalies suivantes :
- balise obligatoire absente ;
- plusieurs occurrences d'une même balise ;
- balise ouverte mais non fermée ;
- balise fermée sans balise d'ouverture correspondante ;
- balise sans contenu ;
- crochet manquant ;
- syntaxe de balise incorrecte ;
- balises imbriquées ;
- nom de balise utilisant une casse incorrecte ;
- contenu ne respectant pas la règle applicable à la balise ;
- duplication d'une combinaison ANACK + ORNUM.
Toute anomalie de ce type constitue une erreur bloquante.
L'application doit, dans la mesure du possible, poursuivre la phase de contrôle afin d'enregistrer dans le journal l'ensemble des anomalies détectables au cours d'une même exécution.
Lorsque seule une balise de casse incorrecte est détectée, l'application journalise `MALFORMED_TAG` pour cette balise et `MISSING_TAG` pour la balise attendue qui reste absente.

## 10. Modèle Markdown

### 10.1 Format

Le document modèle est un fichier Markdown portant l'extension .md.
Il contient la structure du document final ainsi que les emplacements auxquels les résumés doivent être insérés.

### 10.2 Identification des sections

Les emplacements sont identifiés dans le modèle par la syntaxe complète d'une balise ANACK.
Exemple :
[[ANACK]]ACK0130[[/ANACK]]
La valeur présente dans cette balise détermine les documents devant être insérés à cet emplacement.

### 10.3 Validation du modèle

Le modèle doit être un fichier non vide encodé en UTF-8 valide. Il est contrôlé avant les documents PDF. Seules les balises ANACK complètes sont admises : chaque balise doit être correctement formée, fermée, non imbriquée et contenir une clé respectant exactement `ACK` suivi de quatre chiffres ASCII après suppression des seuls espaces périphériques définis au §5.1. Toute balise inconnue, mal formée, non fermée, imbriquée ou contenant une clé invalide rend le modèle invalide. Une clé ANACK ne peut apparaître qu'une seule fois dans le modèle; son doublon est bloquant.
Une non-conformité du contenu du modèle (modèle vide ou balisage/clé invalide) entraîne le code retour 1 et est consignée sous le code `INVALID_TEMPLATE` ou `DUPLICATE_TEMPLATE_ANACK`. Une erreur d'accès au fichier ou un encodage UTF-8 invalide entraîne le code retour 2. La validation d'un modèle invalide n'est pas poursuivie.
À la composition, le marqueur ANACK et sa clé sont remplacés par les résumés et liens correspondants. Si aucun document ne correspond à la clé, le marqueur est retiré et l'emplacement reste vide.

## 11. Correspondance entre le modèle et les documents

Pour chaque document source, la valeur de ANACK est comparée aux clés ANACK présentes dans le modèle.
Une clé ANACK présente dans un document source doit obligatoirement être prévue dans le modèle.
Si un document contient, par exemple :
[[ANACK]]ACK0132[[/ANACK]]
mais que le modèle ne contient pas :
[[ANACK]]ACK0132[[/ANACK]]
le contrôle échoue. Il s'agit d'une erreur bloquante.
À l'inverse, une clé peut être présente dans le modèle sans qu'aucun document source ne lui corresponde. Dans ce cas, la section est laissée vide et aucune erreur ou anomalie n'est générée.

## 12. Ordre de composition

L'ordre général des sections du document final est celui défini par le modèle Markdown.
Lorsque plusieurs documents correspondent à une même clé ANACK, ils sont insérés dans l'ordre numérique croissant de leur valeur ORNUM.
Exemple :
document_C.pdf : ACK0130 / ORNUM 3
document_A.pdf : ACK0130 / ORNUM 1
document_B.pdf : ACK0130 / ORNUM 2
L'ordre d'insertion est :
document_A.pdf
document_B.pdf
document_C.pdf
L'ordre dans lequel les fichiers ont été découverts dans l'arborescence n'a donc aucune incidence sur l'ordre du document final.

## 13. Contenu inséré

Pour chaque document correspondant à une section ANACK, l'application insère :

## 1.	le contenu de sa balise EXSUM ;

## 2.	un lien relatif vers le document PDF source.

Les sauts de ligne contenus dans EXSUM sont conservés.
Lorsque plusieurs documents correspondent à une même clé, chaque résumé et son lien sont insérés successivement dans l'ordre défini par ORNUM.
Un saut de ligne est inséré entre chaque résumé et le lien de sa source, ainsi qu'entre les ensembles résumé/lien de documents successifs.
Les résumés sont traités comme du texte littéral : les caractères actifs de la syntaxe Markdown sont échappés à la composition pour empêcher la création de titres, listes, liens, images ou blocs HTML. Le rendu échappe également le contenu HTML; le HTML brut du modèle n'est pas exécuté. Les sauts de ligne d'un résumé restent préservés.

Le modèle ne peut déclencher le chargement d'aucune ressource réseau ou locale (image, feuille de style, police ou autre ressource). Les références à de telles ressources ne sont pas chargées. Les hyperliens sont conservés comme liens, sans que le moteur de rendu les visite. Seules les ressources livrées avec l'application sont utilisées.

## 14. Processus de traitement

Le traitement est obligatoirement séparé en deux phases.

### 14.1 Phase 1 — Validation

L'application :

## 1.	parcourt récursivement le répertoire --input ;

## 2.	identifie les fichiers PDF ;

## 3.	ignore les fichiers qui ne sont pas au format PDF ;

## 4.	extrait la couche texte de chaque PDF ;

## 5.	recherche les trois balises obligatoires ;

## 6.	vérifie leur structure ;

## 7.	vérifie leur nombre d'occurrences ;

## 8.	valide le contenu de chaque balise ;

## 9.	vérifie l'unicité des couples ANACK + ORNUM ;

## 10.	vérifie que chaque ANACK provenant des documents est prévu dans le modèle ;

## 11.	enregistre les résultats dans le journal.

Aucune composition du document final n'est réalisée pendant cette phase.

### 14.2 Phase 2 — Génération

La phase de génération n'est exécutée que si aucune erreur bloquante n'a été détectée pendant la phase 1.
Une seule erreur bloquante dans un seul document interdit donc la génération de l'ensemble du document final.
Lorsque tous les contrôles sont conformes, l'application :

## 1.	classe les données extraites par clé ANACK ;

## 2.	classe les documents d'une même clé par ORNUM croissant ;

## 3.	insère les résumés et les liens relatifs dans une copie du modèle ;

## 4.	génère le document Markdown final ;

## 5.	génère le document PDF à partir du Markdown.

## 15. Fichiers de sortie existants

L'application ne doit pas écraser automatiquement un document de sortie existant.
Avant toute génération, elle vérifie donc l'existence :
- du fichier PDF demandé ;
- du fichier Markdown correspondant.
Si l'un de ces fichiers existe déjà, la génération est interrompue et une erreur est retournée.
Les fichiers existants restent inchangés.
Le fichier journal est le seul fichier cible qui peut être remplacé : s'il existe, il est écrasé à chaque exécution afin de consigner le résultat le plus récent. Cette exception ne concerne pas les sorties Markdown et PDF.
Les répertoires parents des fichiers de sortie et du journal ne sont pas créés automatiquement. Un répertoire parent absent ou inaccessible entraîne le code retour 2. Le journal ne peut désigner un PDF source, le template ou l'un des fichiers de sortie; les chemins des sorties ne peuvent désigner un fichier source ou le template.

## 16. Génération du PDF

Le document PDF final est généré à partir du document Markdown produit par l'application.
Les paramètres de mise en page sont :
- format de page : A4 ;
- marge supérieure : 2 cm ;
- marge inférieure : 2 cm ;
- marge gauche : 2 cm ;
- marge droite : 2 cm.
Le contenu textuel, la structure Markdown pertinente et les sauts de ligne devant être conservés doivent être restitués de manière cohérente dans le PDF final.

## 17. Journal d'exécution

### 17.1 Format

Le journal est enregistré au format JSON.
Son emplacement est indiqué par l'argument :
`--journal`

### 17.2 Informations générales

Le journal suit le schéma normatif défini dans la spécification technique : il utilise notamment `started_at` au format ISO 8601 avec décalage horaire, `duration_seconds`, `status` (`success`, `validation_failed` ou `execution_failed`), et pour chaque PDF un statut `conforme` ou `non_conforme`.
Le journal contient au minimum :
- la date et l'heure de début de l'exécution, avec décalage horaire ;
- la durée totale de l'exécution ;
- le nombre total de fichiers PDF traités ;
- le résultat de la validation de chaque fichier ;
- le chemin relatif de chaque fichier PDF ;
- les erreurs détectées.
Pour un document ne présentant aucune anomalie, son statut est indiqué comme conforme.
Pour un document présentant une ou plusieurs anomalies, celles-ci sont enregistrées dans le journal.
Lorsque plusieurs erreurs peuvent être détectées dans un même fichier, elles doivent être enregistrées autant que possible afin d'éviter de devoir lancer plusieurs exécutions successives pour découvrir les anomalies une par une.

### 17.3 Exemple indicatif

```json
{
  "schema_version": "1.0",
  "application_version": "1.0.0",
  "started_at": "2026-10-08T09:00:00+02:00",
  "duration_seconds": 3.42,
  "status": "validation_failed",
  "pdf_count": 1,
  "valid_count": 0,
  "invalid_count": 1,
  "files": [
    {
      "path": "subdir/doc2.pdf",
      "status": "non_conforme",
      "errors": [
        {
          "code": "INVALID_ANACK",
          "message": "Format ANACK invalide",
          "tag": "ANACK",
          "page": 2
        }
      ]
    }
  ]
}
```
Les codes et statuts de cet exemple sont normatifs et identiques à ceux de la spécification technique.

## 18. Codes retour

L'application utilise les codes retour suivants :
Code	Signification
0	Exécution réussie, validation conforme et génération terminée
1	Une ou plusieurs non-conformités bloquantes ont été détectées dans les PDF source ou le contenu du modèle
2	Erreur d'exécution ou erreur technique
Les erreurs d'exécution comprennent notamment :
- répertoire d'entrée inexistant ou inaccessible ;
- modèle inexistant ou inaccessible ;
- fichier PDF ou Markdown de sortie déjà existant (`OUTPUT_EXISTS`) ;
- impossibilité d'écrire un fichier de sortie ;
- erreur interne empêchant l'exécution normale.
Une exception du moteur d'extraction qui empêche le traitement normal, distincte d'une source PDF illisible ou corrompue, relève du code 2.

## 19. Affichage en ligne de commande

À la fin de l'exécution, l'application affiche au minimum :
- le nombre de fichiers PDF traités ;
- le temps total écoulé.
Ces informations sont affichées aussi bien en cas de succès qu'en cas d'échec de la validation, dès lors que l'exécution a pu atteindre la fin de la phase de contrôle.

## 20. Cas de test et critères d'acceptation

Les cas suivants constituent le socle minimal des tests fonctionnels.
| ID | Catégorie | Cas testé | Donnée de test | Résultat attendu | Bloquant |
|---|---|---|---|---|---|
| T001 | Général | Document conforme | 1 ANACK, 1 ORNUM et 1 EXSUM valides | Document conforme | Non |
| T002 | ANACK | Format valide | [[ANACK]]ACK0130[[/ANACK]] | ACK0130 extrait | Non |
| T003 | ANACK | Pas assez de chiffres | [[ANACK]]ACK130[[/ANACK]] | ANACK invalide | Oui |
| T004 | ANACK | Trop de chiffres | [[ANACK]]ACK01300[[/ANACK]] | ANACK invalide | Oui |
| T005 | ANACK | Mauvaise casse | [[ANACK]]ack0130[[/ANACK]] | ANACK invalide | Oui |
| T006 | ANACK | Espaces périphériques | [[ANACK]] ACK0130 [[/ANACK]] | ACK0130 accepté | Non |
| T007 | ANACK | Mauvaise casse de balise | [[anack]]ACK0130[[/anack]] | Balise incorrecte | Oui |
| T008 | ANACK | Deux ANACK | Deux occurrences dans le PDF | Erreur de duplication | Oui |
| T009 | ORNUM | Valeur valide | [[ORNUM]]2[[/ORNUM]] | 2 extrait | Non |
| T010 | ORNUM | Deux chiffres | [[ORNUM]]10[[/ORNUM]] | ORNUM invalide | Oui |
| T011 | ORNUM | Non numérique | [[ORNUM]]A[[/ORNUM]] | ORNUM invalide | Oui |
| T012 | ORNUM | Espaces | [[ORNUM]] 2 [[/ORNUM]] | 2 accepté | Non |
| T013 | ORNUM | Deux balises ORNUM | Deux occurrences dans le PDF | Erreur de duplication | Oui |
| T014 | EXSUM | Texte simple | [[EXSUM]]This is the summary.[[/EXSUM]] | Texte extrait | Non |
| T015 | EXSUM | Texte et chiffres | [[EXSUM]]Version 2 of the process.[[/EXSUM]] | Texte extrait | Non |
| T016 | EXSUM | Commence par ACK | [[EXSUM]]ACK document summary[[/EXSUM]] | EXSUM invalide | Oui |
| T017 | EXSUM | Commence par chiffre | [[EXSUM]]2 documents reviewed[[/EXSUM]] | EXSUM invalide | Oui |
| T018 | EXSUM | Vide | [[EXSUM]][[/EXSUM]] | Erreur de contenu | Oui |
| T019 | EXSUM | Espaces périphériques | Résumé entouré d'espaces | Espaces périphériques supprimés | Non |
| T020 | EXSUM | Saut de ligne | Résumé sur deux lignes | Accepté ; saut de ligne conservé | Non |
| T021 | EXSUM | Plusieurs sauts de ligne | Résumé multiligne | Accepté ; sauts conservés | Non |
| T022 | EXSUM | Deux EXSUM | Deux occurrences | Erreur de duplication | Oui |
| T023 | Structure | Ouverture sans fermeture | [[EXSUM]]texte | Erreur de structure | Oui |
| T024 | Structure | Fermeture sans ouverture | texte[[/EXSUM]] | Erreur de structure | Oui |
| T025 | Structure | Crochet manquant | [EXSUM]]texte[[/EXSUM]] | Balise mal formée | Oui |
| T026 | Structure | Fermeture mal formée | [[EXSUM]]texte[/EXSUM]] | Balise mal formée | Oui |
| T027 | Structure | Balises imbriquées | ORNUM à l'intérieur d'EXSUM | Erreur d'imbrication | Oui |
| T028 | Structure | ANACK absent | ORNUM + EXSUM seulement | ANACK manquant | Oui |
| T029 | Structure | ORNUM absent | ANACK + EXSUM seulement | ORNUM manquant | Oui |
| T030 | Structure | EXSUM absent | ANACK + ORNUM seulement | EXSUM manquant | Oui |
| T031 | PDF | Couche texte | PDF texte valide | PDF analysé | Non |
| T032 | PDF | Scan sans texte | PDF image uniquement | Erreur, aucun OCR | Oui |
| T033 | PDF | PDF corrompu | PDF illisible | Non-conformité de la source journalisée, code 1 | Oui |
| T034 | Entrée | Fichier non PDF | TXT, JPG, DOCX | Ignoré | Non |
| T035 | Template | Clé correspondante | ACK0130 des deux côtés | Résumé et lien insérés | Non |
| T036 | Template | Clé sans document | ACK uniquement dans le modèle | Section vide, aucune erreur | Non |
| T037 | Template | Clé PDF absente du modèle | ACK0132 uniquement dans PDF | Erreur | Oui |
| T038 | Ordre | Plusieurs documents | ORNUM 1, 2, 3 | Insertion 1, 2, 3 | Non |
| T039 | Ordre | Ordre de découverte différent | Découverte 3, 1, 2 | Insertion 1, 2, 3 | Non |
| T040 | Ordre | ORNUM dupliqué pour un ANACK | Deux ACK0130 / 2 | Erreur de duplication | Oui |
| T041 | Ordre | Même ORNUM, ANACK différents | ACK0130/2, ACK0140/2 | Accepté | Non |
| T042 | Liens | Lien source | PDF dans sous-répertoire | Lien relatif correct | Non |
| T043 | Liens | Arborescence profonde | PDF plusieurs niveaux plus bas | Lien relatif correct | Non |
| T044 | Génération | Ensemble conforme | Tous les contrôles passent | .md et .pdf créés | Non |
| T045 | Génération | Une erreur | Un PDF invalide | Aucun document final généré | Oui |
| T046 | Validation | Plusieurs erreurs | Plusieurs PDF invalides | Toutes les erreurs détectables journalisées | Oui |
| T047 | Sortie | PDF existe | PDF cible déjà présent | Pas d'écrasement, `OUTPUT_EXISTS`, code 2 | Oui |
| T048 | Sortie | MD existe | Markdown cible déjà présent | Pas d'écrasement, `OUTPUT_EXISTS`, code 2 | Oui |
| T049 | Sortie | Nom de sortie | ack-doc.pdf | ack-doc.pdf + ack-doc.md | Non |
| T050 | PDF final | Mise en page | Génération normale | A4, marges de 2 cm | Non |
| T051 | Journal | Succès | Jeu conforme | JSON valide et complet | Non |
| T052 | Journal | Non-conformité | PDF invalide | Erreur présente dans JSON | Oui |
| T053 | Journal | PDF corrompu | PDF illisible | Non-conformité et chemin journalisés, code 1 | Oui |
| T054 | Journal | Chemin | PDF dans sous-répertoire | Chemin relatif journalisé | Non |
| T055 | CLI | Succès | Traitement réussi | Code 0 | Non |
| T056 | CLI | Non-conformité | Validation échouée | Code 1 | Oui |
| T057 | CLI | Erreur technique | Erreur d'exécution | Code 2 | Oui |
| T058 | CLI | Input inexistant | Mauvais --input | Code 2 | Oui |
| T059 | CLI | Template inexistant | Mauvais --template | Code 2 | Oui |
| T060 | CLI | Sortie impossible | Destination inaccessible | Code 2 | Oui |
| T061 | Affichage | Succès | Exécution normale | Nombre de PDF + durée affichés | Non |
| T062 | Affichage | Validation échouée | Documents non conformes | Nombre analysé + durée affichés | Non |
| T063 | Template | Modèle vide | Fichier vide | `INVALID_TEMPLATE`, code 1, aucune génération | Oui |
| T064 | Template | Clé ANACK invalide | Marqueur avec clé ne respectant pas `ACK` + 4 chiffres ASCII | `INVALID_TEMPLATE`, code 1 | Oui |
| T065 | Template | ANACK dupliqué | Deux marqueurs identiques dans le modèle | `DUPLICATE_TEMPLATE_ANACK`, code 1 | Oui |
| T066 | Template | Balise mal formée ou inconnue | Marqueur incomplet ou balise autre que ANACK | `INVALID_TEMPLATE`, code 1 | Oui |
| T067 | PDF | Marqueur fragmenté par espaces/sauts de ligne | Séparateurs ASCII entre caractères d'un marqueur, même page | Marqueur reconnu | Non |
| T068 | PDF | Marqueur réparti sur deux pages | Fragments de marqueur de part et d'autre d'une frontière de page | Erreur de structure, code 1 | Oui |
| T069 | EXSUM | Résumé traversant deux pages | Début et fin du résumé sur des pages différentes | `EXSUM_CROSSES_PAGE`, code 1 | Oui |
| T070 | ANACK | Espace Unicode périphérique | NBSP en tête de `ACK0130` | Pas de suppression Unicode; `INVALID_ANACK`, code 1 | Oui |
| T071 | EXSUM | Syntaxe Markdown active | Résumé contenant `#`, `*`, `[lien](...)` ou HTML | Rendu en texte littéral, sans structure ou contenu actif | Non |
| T072 | Template | Ressources externes ou locales | Référence image/CSS distante ou locale | Aucune ressource chargée | Non |
| T073 | Entrée | Aucun PDF trouvé | Répertoire d'entrée vide de PDF | `NO_PDF_FOUND`, code 1, journal produit | Oui |
| T074 | Chemins | Chemin relatif des arguments | Arguments relatifs lancés depuis un répertoire courant connu | Résolution depuis le répertoire courant | Non |
| T075 | Liens | Référentiel du lien source | PDF sous un sous-répertoire de `--input` | Lien relatif calculé depuis le Markdown final | Non |
| T076 | Sortie | Répertoire parent absent | Dossier cible inexistant | Pas de création implicite, code 2 | Oui |
| T077 | Journal | Journal existant | Journal déjà présent | Journal remplacé par le résultat de l'exécution | Non |
| T078 | Ordre | ORNUM égal à zéro | Deux documents avec ORNUM 0 et 1 | Le document ORNUM 0 est inséré en premier | Non |
| T079 | Structure | Balise avec casse incorrecte | `[[anack]]...[[/anack]]` seul | `MALFORMED_TAG` et `MISSING_TAG` pour ANACK | Oui |
| T080 | EXSUM | Casse du préfixe interdit | Résumé commençant par `ack` en minuscules | Accepté; la règle interdit uniquement le préfixe littéral majuscule `ACK` | Non |
| T081 | Template | Encodage invalide | Séquence UTF-8 invalide | Erreur technique, code 2 | Oui |
| T082 | Template | Lecture impossible | Fichier modèle inaccessible | Erreur technique, code 2 | Oui |
| T083 | EXSUM | Espace Unicode | Résumé contenant un NBSP périphérique | `INVALID_EXSUM`, code 1; aucune normalisation Unicode | Oui |

## 21. Critères globaux d'acceptation

L'application ACK-DOC est considérée conforme à la présente spécification lorsque :

## 1.	elle fonctionne sous Debian 13 avec Python 3 ;

## 2.	elle fonctionne exclusivement en ligne de commande ;

## 3.	elle parcourt récursivement les PDF du répertoire d'entrée ;

## 4.	elle n'effectue aucun OCR ;

## 5.	elle détecte les erreurs de balisage définies dans la présente spécification ;

## 6.	elle n'autorise qu'une occurrence de chaque balise par document ;

## 7.	elle contrôle le format des contenus ANACK, ORNUM et EXSUM ;

## 8.	elle détecte les doublons ANACK + ORNUM ;

## 9.	elle contrôle la correspondance des clés des documents avec le modèle ;

## 10.	elle ne génère aucun document final en présence d'une erreur bloquante ;

## 11.	elle classe les documents d'une même clé selon ORNUM croissant ;

## 12.	elle conserve les sauts de ligne des résumés ;

## 13.	elle produit des liens relatifs vers les PDF source ;

## 14.	elle produit un Markdown et un PDF en cas de validation réussie ;

## 15.	le PDF est au format A4 avec des marges périphériques de 2 cm ;

## 16. elle n'écrase pas les fichiers de sortie Markdown/PDF existants et remplace le journal existant ;

## 17.	elle génère un journal JSON exploitable ;

## 18.	elle retourne le code d'exécution correspondant au résultat ;

## 19.	elle affiche le nombre de PDF traités et la durée totale d'exécution ;

## 20.	les cas de test définis dans la présente spécification produisent les résultats attendus.

## 22. Environnement cible

L'environnement cible est :
Système d'exploitation : Debian 13
**Langage  :** Python 3
Interface : ligne de commande
Entrées documentaires : PDF avec couche texte
Modèle : Markdown
Sorties : Markdown + PDF
Journal : JSON
OCR : non
Les bibliothèques Python et composants nécessaires à l'extraction des PDF, au traitement Markdown et à la génération du PDF seront déterminés lors de la conception technique, sous réserve qu'ils permettent de respecter l'ensemble des exigences de la présente spécification.
