# Éclairage sur les choix de conception techniques pour ACK-DOC

À partir de la spécification actuelle, je recommande des choix techniques assez conservateurs : **peu de dépendances, séparation nette des responsabilités, validation déterministe avant toute génération**, et surtout pas de traitement « intelligent » qui chercherait à réparer silencieusement les PDF.

## Architecture recommandée

Je structurerais ACK-DOC comme une petite chaîne de traitement en six composants indépendants :

```text
CLI
 │
 ├── Validation des paramètres
 │
 ├── Découverte des PDF
 │
 ├── Extraction texte PDF
 │       ↓
 │   Analyse / validation des balises
 │       ↓
 │   Modèle de données interne
 │
 ├── Validation croisée avec le template
 │
 ├── Composition Markdown
 │
 └── Conversion Markdown → HTML → PDF
         +
       Journal JSON
```

Cette séparation est importante : **le composant qui lit les PDF ne doit pas connaître le template, et le composant qui produit le PDF final ne doit pas avoir à revalider les documents**.

## 1. Extraction du texte PDF : PyMuPDF

Je choisirais **PyMuPDF** comme moteur principal.

Il propose différents modes d'extraction du texte, notamment l'extraction simple, le tri par blocs et la reproduction de la disposition physique.

Pour ACK-DOC, je privilégierais l'extraction texte simple, page par page, sans tentative de reconstruction de la disposition visuelle. C'est exactement cohérent avec votre règle : *la balise est recherchée dans le texte extrait, pas selon sa position graphique*.

Je déconseillerais de demander à la bibliothèque de « corriger » automatiquement l'ordre de lecture. Plus on utilise des heuristiques de disposition, plus le résultat risque de changer suivant la structure interne du PDF.

**Alternative : `pypdf`.** C'est également une très bonne bibliothèque et elle est activement maintenue. Je la garderais éventuellement comme outil de comparaison pendant les tests, mais **pas comme deuxième moteur automatique de secours**.

C'est important : je déconseille fortement une logique telle que :

```text
PyMuPDF échoue
→ essayons pypdf
→ si pypdf arrive à lire quelque chose, considérons le PDF conforme
```

Cela rendrait le comportement difficilement reproductible. Un document doit donner un résultat déterministe avec **un seul moteur d'extraction officiellement choisi**.

## 2. Distinguer « PDF illisible » et « texte vide »

Je prévoirais trois situations différentes :

```text
PDF impossible à ouvrir
    → erreur technique / lecture

PDF ouvert, mais aucune couche texte exploitable
    → non-conformité du document

PDF ouvert et texte extrait
    → analyse des balises
```

Cette distinction sera très utile dans le journal JSON.

Je conserverais également une notion de page pendant l'extraction :

```python
pages = [
    "...texte page 1...",
    "...texte page 2...",
]
```

plutôt que de concaténer immédiatement tout le document.

Cela permet notamment d'identifier plus tard qu'une anomalie se trouve page 7 sans devoir refaire toute l'architecture.

## 3. Balises coupées par un saut de page

Il reste un cas à fixer :

```text
page 3 :
[[EXSUM]]Début du résumé...

page 4 :
...fin du résumé[[/EXSUM]]
```

Je recommanderais **d'autoriser également ce cas**, à condition que le texte extrait des pages soit concaténé avec un séparateur contrôlé.

Pourquoi ? Un changement de pagination du document source ne devrait idéalement pas rendre le document non conforme.

Il faut en revanche définir comment le saut de page est restitué. Je conseillerais de le transformer en **saut de ligne**, et non de provoquer automatiquement un saut de page dans le résumé final.

## 4. Ne pas utiliser une seule grosse expression régulière pour analyser les balises

On pourrait être tenté d'écrire :

```python
r"\[\[EXSUM\]\](.*?)\[\[/EXSUM\]\]"
```

et trois expressions régulières semblables.

Cela fonctionne pour le cas nominal, mais devient rapidement mauvais pour détecter :

- ouverture sans fermeture ;
- fermeture sans ouverture ;
- crochets manquants ;
- balises imbriquées ;
- doublons ;
- balises mal orthographiées.

Je construirais plutôt un **petit analyseur de balises**.

Conceptuellement :

```text
lecture du texte
     ↓
détection des marqueurs [[...]]
     ↓
classification :
    ouverture
    fermeture
    balise inconnue
    structure incorrecte
     ↓
machine d'état
     ↓
liste d'anomalies
```

Les expressions régulières restent excellentes pour **valider le contenu** :

```text
ANACK → ^ACK[0-9]{4}$
ORNUM → ^[0-9]$
```

mais elles ne devraient pas être responsables de toute l'analyse structurelle.

Cette séparation rendra aussi les tests T023 à T030 beaucoup plus simples.

## 5. Conserver deux valeurs pour chaque contenu

Pour chacune des balises, je conserverais :

```text
raw_value
normalized_value
```

Par exemple :

```text
raw_value        = " ACK0130 "
normalized_value = "ACK0130"
```

Cela permet de respecter la règle de suppression des espaces sans perdre la valeur réellement trouvée dans le PDF.

Pour `EXSUM`, il faut être particulièrement prudent. Je n'utiliserais surtout pas :

```python
" ".join(text.split())
```

car cela détruirait les sauts de ligne.

Je ferais uniquement une suppression des caractères d'espacement **en début et en fin de contenu**, en conservant l'intérieur du résumé.

## 6. Représentation interne : des objets, pas des dictionnaires partout

Une fois un PDF validé, je le représenterais par un objet de données très simple, par exemple :

```text
SourceDocument
    path
    relative_path
    anack
    ornum
    exsum
```

et pour une erreur :

```text
ValidationIssue
    code
    message
    file
    page éventuelle
    tag éventuelle
```

En Python moderne, des `dataclass` conviennent parfaitement.

L'intérêt est considérable : le reste du programme ne manipule plus le PDF.

La génération travaille uniquement avec quelque chose qui ressemble à :

```text
ACK0130
    1 → document_a.pdf → résumé...
    2 → document_b.pdf → résumé...
    3 → document_c.pdf → résumé...

ACK0140
    1 → document_x.pdf → résumé...
```

## 7. Donner un code stable à chaque erreur

Dans le JSON, je déconseille de stocker seulement :

```json
"Contenu ANACK invalide"
```

Je préférerais :

```json
{
  "code": "INVALID_ANACK",
  "message": "Le contenu de la balise ANACK ne respecte pas le format ACK + 4 chiffres.",
  "value": "ACK130"
}
```

Par exemple, l'application pourrait avoir des codes tels que :

```text
MISSING_TAG
DUPLICATE_TAG
UNCLOSED_TAG
UNMATCHED_CLOSING_TAG
MALFORMED_TAG
NESTED_TAG
INVALID_ANACK
INVALID_ORNUM
INVALID_EXSUM
DUPLICATE_ANACK_ORNUM
ANACK_NOT_IN_TEMPLATE
PDF_UNREADABLE
PDF_NO_TEXT
OUTPUT_EXISTS
```

Le **code** reste stable pour les traitements automatisés ; le **message** peut évoluer et être rendu plus explicite.

C'est un petit investissement qui apporte beaucoup de valeur.

## 8. Template : remplacement contrôlé, pas moteur de template généraliste

Je ne mettrais pas Jinja2 ou un moteur équivalent dans ce projet.

Votre besoin est beaucoup plus simple :

```text
[[ANACK]]ACK0130[[/ANACK]]
```

est un marqueur de substitution.

Je traiterais donc le Markdown comme du texte et je rechercherais exactement ces marqueurs.

Cela limite fortement les effets de bord et rend le format du template compréhensible par quelqu'un qui ne connaît pas Python.

Une autre bonne règle serait de **valider le template avant les PDF** :

- fichier lisible ;
- marqueurs `ANACK` syntaxiquement valides ;
- éventuellement absence de doublons de la même clé.

Sur ce dernier point, je suggère d'ajouter à la spécification :

> Une même clé ANACK ne peut apparaître qu'une seule fois dans le template.

Sinon, `ACK0130` présent deux fois pose la question : faut-il injecter les mêmes résumés deux fois ?

## 9. Composition du Markdown

Je prévoirais une fonction unique dont l'entrée ressemble à :

```text
template
+
{
    ACK0130: [doc1, doc2],
    ACK0140: [doc3]
}
```

et dont la sortie est simplement une chaîne Markdown.

Cela rend le composant **entièrement testable sans aucun PDF**.

Pour chaque source, le rendu pourrait être par exemple :

```markdown
Résumé du document...

[Document source](../documents/dossier/document.pdf)
```

Je recommande de **définir précisément ce fragment dans la spécification**. C'est l'un des quelques choix fonctionnels encore implicites.

## 10. Markdown → HTML → PDF plutôt que Markdown → PDF directement

Je choisirais la chaîne :

```text
Markdown
   ↓
markdown-it-py
   ↓
HTML
   ↓
CSS
   ↓
WeasyPrint
   ↓
PDF
```

`markdown-it-py` est un parseur CommonMark configurable et extensible qui produit notamment du HTML à partir du Markdown.

Je préfère cette solution à l'appel d'un gros outil externe de type traitement de texte parce que vous gardez beaucoup de contrôle sur le processus.

Pour le PDF, **WeasyPrint** est bien adapté à ce genre de document.

## 11. La mise en page doit être définie en CSS

C'est beaucoup plus propre que d'essayer de contrôler la mise en page depuis Python.

Par exemple :

```css
@page {
    size: A4;
    margin: 2cm;
}
```

Puis une feuille CSS maîtriserait :

- police ;
- tailles de titres ;
- interligne ;
- paragraphes ;
- liens ;
- tableaux ;
- sauts de page éventuels.

Le Python resterait donc concentré sur les règles métier.

Je recommande aussi d'embarquer cette feuille CSS dans l'application plutôt que d'utiliser un style dépendant de la machine.

## 12. Dépendances : versions verrouillées

Comme il s'agit vraisemblablement d'un outil métier, je ne ferais pas :

```text
pip install pymupdf weasyprint markdown-it-py
```

sans contrôle de version.

Je prévoirais :

```text
pyproject.toml
+
fichier de verrouillage des dépendances
```

et une procédure explicite pour mettre à niveau les bibliothèques après exécution des tests de non-régression.

C'est particulièrement important pour **l'extraction PDF** : une nouvelle version d'un moteur peut modifier subtilement la façon dont certains textes sont extraits.

Le corpus de PDF Adobe, PDF issus d'imprimantes virtuelles et PDF issus des applications métier deviendra alors le **corpus de non-régression**.

## 13. Le corpus de PDF est presque plus important que les tests unitaires

Je constituerais trois niveaux de tests :

### Tests unitaires

Tests de l'analyseur de balises avec de simples chaînes de caractères.

### Tests d'intégration

Vrais PDF contenant les cas T001–T062.

### Tests de non-régression PDF

Documents produits par chacune des sources réelles.

Par exemple :

```text
Adobe Acrobat
Impression PDF système
Application métier A
Application métier B
...
```

Je conserverais au moins quelques PDF de référence par origine.

C'est indispensable parce que deux fichiers qui semblent identiques à l'écran peuvent avoir des couches texte très différentes.

## 14. Le journal JSON devrait avoir un schéma versionné

Je proposerais quelque chose comme :

```json
{
  "schema_version": "1.0",
  "application_version": "1.0.0",
  "started_at": "...",
  "duration_seconds": 2.41,
  "status": "validation_failed",
  "pdf_count": 17,
  "valid_count": 16,
  "invalid_count": 1,
  "files": []
}
```

La présence de :

```text
schema_version
application_version
```

est très utile.

Dans deux ans, si la structure évolue, on saura exactement comment interpréter les anciens journaux.

## 15. Les écritures finales devraient être atomiques

Je ne générerais pas directement :

```text
rapport.md
rapport.pdf
```

Le processus devrait plutôt être :

```text
générer rapport.md.tmp
générer rapport.pdf.tmp
vérifier le succès
↓
renommer atomiquement :
rapport.md.tmp  → rapport.md
rapport.pdf.tmp → rapport.pdf
```

Ainsi, si WeasyPrint échoue en cours de génération, on ne laisse pas un faux `rapport.pdf` incomplet donnant l'impression que le traitement a réussi.

Les fichiers temporaires peuvent être nettoyés en cas d'erreur.

## 16. Attention au code retour `1` versus `2`

Je formaliserais très nettement :

```text
0 = les données sont conformes et les sorties ont été créées

1 = ACK-DOC a fonctionné normalement,
    mais il a découvert une non-conformité documentaire

2 = ACK-DOC n'a pas pu accomplir correctement son travail
    à cause d'un problème technique
```

Cette distinction est très saine pour une utilisation automatisée.

Par exemple :

```text
ANACK incorrect       → 1
ORNUM dupliqué        → 1
PDF sans couche texte → 1

permissions refusées   → 2
template introuvable   → 2
disque plein           → 2
bibliothèque en erreur → 2
```

Je classerais **PDF corrompu** en `1` ou `2` selon ce que vous souhaitez exprimer métier. Dans votre contexte, je serais plutôt tenté de le classer **1 : document source non exploitable**, même si techniquement il s'agit d'une erreur de lecture.

## 17. Portabilité : ne pas viser en premier lieu un exécutable monolithique

Comme la cible est précisément **Debian 13**, je privilégierais une application Python installée dans un environnement isolé plutôt qu'un exécutable unique.

Par exemple :

```text
ACK-DOC/
├── venv/
├── ack_doc/
├── resources/
│   └── pdf.css
├── pyproject.toml
└── lancement
```

ou, mieux encore pour une exploitation maîtrisée, un paquet Debian interne.

Faire un binaire unique avec PyInstaller reste possible, mais WeasyPrint dépend lui-même de composants de rendu système. Le bénéfice d'un « exécutable Linux unique » est donc moins évident qu'il n'y paraît et rend souvent la maintenance plus compliquée.

## Choix de pile recommandé

| Fonction | Choix |
|---|---|
| Langage | Python 3 |
| CLI | `argparse` de la bibliothèque standard |
| Parcours fichiers | `pathlib` |
| Extraction PDF | **PyMuPDF** |
| Analyse des balises | **analyseur maison / machine d'état** |
| Validation des valeurs | expressions régulières Python |
| Modèle interne | `dataclasses` |
| Journal | module standard `json` |
| Markdown | **markdown-it-py** |
| PDF | **WeasyPrint** |
| Mise en page | CSS embarqué |
| Tests | `pytest` |
| Packaging | environnement Python verrouillé ou paquet Debian |
| Configuration | aucune configuration externe tant qu'elle n'est pas nécessaire |

Cette architecture est volontairement peu sophistiquée. Pour ACK-DOC, c'est un avantage : **les règles métier sont petites, strictes et auditables**, et il vaut mieux pouvoir expliquer exactement pourquoi un document a été rejeté que disposer d'un moteur très permissif.

## Décisions à ajouter à la spécification

Les deux décisions que j'ajouterais maintenant sont :

1. **Interdire les doublons ANACK dans le template.**
2. **Définir le traitement des EXSUM qui traversent un changement de page.**

Une fois ces deux points tranchés, l'architecture est suffisamment définie pour passer à une véritable spécification technique puis au développement.
