# ACK-DOC — Spécification technique de conception

**Référence :** ACK-DOC-ST-001  
**Version :** 1.0  
**Date :** 8 octobre 2026  
**Statut :** Proposition de référence pour le développement  
**Environnement :** Debian 13 / Python 3  
**Nature :** Application en ligne de commande

Cette spécification traduit les choix techniques retenus en exigences de conception directement applicables. Elle complète la spécification fonctionnelle ACK-DOC sans la remplacer.

Les termes **DOIT**, **NE DOIT PAS** et **DEVRAIT** sont normatifs. Les exigences `TEC-xxx` doivent pouvoir être vérifiées.

## 1. Principes généraux

| Référence | Exigence |
|---|---|
| TEC-001 | L'application DOIT être développée en Python 3 et fonctionner sous Debian 13. |
| TEC-002 | L'application DOIT fonctionner exclusivement en ligne de commande. |
| TEC-003 | Les traitements de validation et de génération DOIVENT être séparés. |
| TEC-004 | Aucune génération finale ne DOIT être entreprise avant validation complète des entrées. |
| TEC-005 | L'application NE DOIT PAS corriger silencieusement les données non conformes. |
| TEC-006 | À entrées, configuration et versions de dépendances identiques, les résultats fonctionnels DOIVENT être reproductibles. |
| TEC-007 | Les dépendances Python DOIVENT être déclarées et leurs versions verrouillées. |

## 2. Architecture logicielle

```text
CLI — argparse
  |
  +-- Validation des paramètres
  +-- Découverte des PDF
  +-- Lecture et validation du template
  +-- Extraction PDF — PyMuPDF
  |     +-- Analyse syntaxique des balises
  |     +-- Validation des contenus
  |     +-- Modèle de données interne
  +-- Validation croisée ANACK / template
  +-- Décision de génération
        +-- Échec : journal JSON, code retour 1 ou 2
        +-- Succès : Markdown -> HTML/CSS -> PDF
  +-- Journal JSON
```

| Module | Responsabilité |
|---|---|
| `cli.py` | Arguments, orchestration et codes retour |
| `discovery.py` | Parcours récursif et inventaire des PDF |
| `pdf_reader.py` | Extraction du texte et informations de page |
| `tag_parser.py` | Analyse syntaxique des balises |
| `validators.py` | Validation des valeurs et règles métier |
| `template.py` | Lecture et validation du modèle Markdown |
| `models.py` | Structures de données internes |
| `composer.py` | Composition du Markdown final |
| `renderer.py` | Conversion Markdown, HTML et PDF |
| `journal.py` | Production du journal JSON |
| `errors.py` | Codes et catégories d'erreurs |

- **TEC-008** — Chaque module DOIT disposer d'une responsabilité principale clairement délimitée.
- **TEC-009** — Le moteur de génération NE DOIT PAS relire les PDF source.
- **TEC-010** — La composition Markdown DOIT être testable indépendamment de l'extraction PDF.

## 3. Extraction des documents PDF

La bibliothèque retenue est **PyMuPDF**.

- **TEC-011** — PyMuPDF DOIT être l'unique moteur d'extraction utilisé en production.
- **TEC-012** — Le texte DOIT être extrait page par page.
- **TEC-013** — L'extraction DOIT utiliser le texte interne du PDF et non la position visuelle des caractères.
- **TEC-014** — Aucun OCR ne DOIT être exécuté.
- **TEC-015** — Le numéro de page DOIT rester disponible pour localiser les erreurs.
- **TEC-016** — Un PDF sans texte exploitable DOIT être déclaré non conforme.
- **TEC-017** — Un PDF impossible à ouvrir DOIT être signalé dans le journal.
- **TEC-018** — Aucun moteur alternatif ne DOIT être déclenché automatiquement après un échec d'extraction.

Les pages sont représentées par des structures contenant leur numéro et le texte extrait. La concaténation destinée à l'analyse utilise un séparateur explicite de frontière de page, qui ne peut être supprimé par la normalisation.

- **TEC-076** — Une impossibilité d'ouvrir ou de lire un PDF, ainsi qu'un PDF corrompu ou dépourvu de texte exploitable, DOIT être classé comme une non-conformité de la source et entraîner le code retour `1`. Une exception attribuable au moteur d'extraction ou à l'application DOIT être classée comme erreur technique et entraîner le code retour `2`.

### 3.1 Altérations prévisibles de l'extraction

L'extraction de texte peut introduire des espaces ou des retours à la ligne à l'intérieur d'un marqueur, notamment lorsque son rendu est fragmenté. La tolérance porte uniquement sur les caractères d'espacement ASCII insérés à l'intérieur du texte d'un marqueur, sur une même page. Le parseur peut les ignorer pour reconnaître les marqueurs attendus. Il NE DOIT PAS supprimer ces caractères dans les contenus des balises ni les supprimer pour franchir une frontière de page.

- **TEC-077** — Un marqueur dont les caractères sont séparés uniquement par des espaces ou sauts de ligne ASCII sur une même page DOIT être reconnu comme le marqueur correspondant.
- **TEC-078** — Un marqueur mal formé qui ne peut pas être reconnu par cette règle DOIT produire `MALFORMED_TAG`; l'absence subséquente d'une balise obligatoire DOIT également être signalée par `MISSING_TAG`.
- **TEC-079** — Un marqueur réparti sur plusieurs pages DOIT produire `MALFORMED_TAG`. Un contenu `EXSUM` réparti sur plusieurs pages DOIT produire `EXSUM_CROSSES_PAGE`. Le texte extrait de pages différentes NE DOIT PAS être fusionné pour rendre conforme un marqueur ou un résumé fragmenté.

## 4. Analyse syntaxique des balises

Le programme utilise un **analyseur déterministe à états**, développé spécifiquement pour ACK-DOC. Il distingue les marqueurs d'ouverture, les marqueurs de fermeture, le contenu, les anomalies syntaxiques et les imbrications.

- **TEC-019** — L'analyseur DOIT identifier les trois types de balises `ANACK`, `ORNUM` et `EXSUM`.
- **TEC-020** — Il DOIT détecter les balises absentes, dupliquées, non fermées, fermées sans ouverture, imbriquées et mal formées.
- **TEC-021** — Les noms des balises DOIVENT respecter strictement la casse.
- **TEC-022** — L'analyseur DOIT retourner les valeurs extraites ainsi qu'une collection structurée d'anomalies.
- **TEC-023** — Une anomalie détectée dans un document NE DOIT PAS interrompre le contrôle des autres documents, sauf si une erreur technique empêche la poursuite.

### 4.1 Validation des contenus

| Balise | Règle après suppression des espaces périphériques |
|---|---|
| ANACK | `^ACK[0-9]{4}$` |
| ORNUM | `^[0-9]$` |
| EXSUM | Non vide, ne commence pas par le préfixe littéral `ACK` (sensible à la casse) ni par un chiffre ASCII |

La validation d'`EXSUM` préserve les sauts de ligne internes. Le retrait périphérique est limité aux caractères ASCII espace (`U+0020`), tabulation (`U+0009`), saut de ligne (`U+000A`) et retour chariot (`U+000D`). Les espaces Unicode et autres caractères de contrôle ne sont pas supprimés silencieusement et rendent la valeur invalide. La règle « ne commence pas par ACK » est sensible à la casse et porte sur le préfixe littéral majuscule `ACK`; le premier caractère ne doit pas être un chiffre ASCII. Le texte Unicode (lettres et ponctuation) est accepté dans le reste du résumé.

### 4.2 Conservation des valeurs

Chaque contenu est représenté par `raw_value` (valeur extraite) et `normalized_value` (valeur après suppression des espaces périphériques).

- **TEC-024** — La normalisation NE DOIT PAS modifier les espaces ni les sauts de ligne internes d'`EXSUM`.
- **TEC-025** — Les contenus invalides NE DOIVENT PAS être automatiquement corrigés pour devenir conformes.
- **TEC-080** — La même liste explicite de caractères ASCII périphériques (`U+0020`, `U+0009`, `U+000A`, `U+000D`) DOIT être appliquée aux valeurs ANACK, ORNUM et EXSUM. Aucun changement de casse, normalisation Unicode ou remplacement de caractère ne DOIT être appliqué.

## 5. Modèle de données

Les structures internes sont implémentées avec des `dataclasses` Python annotées.

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True)
class SourceDocument:
    path: Path
    relative_path: Path
    anack: str
    ornum: int
    exsum: str

@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    file: str | None = None
    page: int | None = None
    tag: str | None = None

@dataclass
class ValidationResult:
    documents: list[SourceDocument] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues
```

- **TEC-026** — Les modules de composition DOIVENT consommer uniquement des documents validés.
- **TEC-027** — Les erreurs DOIVENT être représentées par des objets structurés comportant un code stable et un message lisible.
- **TEC-028** — Les chemins des documents source DOIVENT être conservés pour les liens et le journal.

## 6. Validation du template Markdown

Le template est lu comme un fichier texte UTF-8 strict et non vide. Sa validation est dédiée au rôle de template et reprend les contrôles structurels de balisage applicables aux PDF, sans exiger de balises ORNUM ou EXSUM : seuls les marqueurs ANACK complets sont autorisés et chacun fournit une clé de section. La clé respecte exactement `^ACK[0-9]{4}$`. Toute balise inconnue, mal formée, non fermée, imbriquée, dupliquée ou toute clé invalide bloque la validation. Les espaces périphériques d'une clé sont retirés selon la règle commune de normalisation.

Les marqueurs de substitution respectent la syntaxe :

```text
[[ANACK]]ACK0130[[/ANACK]]
```

- **TEC-029** — Le modèle DOIT être validé avant la validation croisée avec les documents source.
- **TEC-030** — Une clé `ANACK` présente dans un document source mais absente du modèle DOIT provoquer une erreur bloquante.
- **TEC-031** — Une clé présente dans le modèle mais sans document correspondant DOIT produire un emplacement vide, sans anomalie.
- **TEC-032** — La substitution des marqueurs DOIT être effectuée par un mécanisme spécifique, sans moteur de templates généraliste.
- **TEC-033** — L'ordre des sections du modèle DOIT être conservé.
- **TEC-034** — Les documents associés à une même clé DOIVENT être classés par `ORNUM` croissant.
- **TEC-035** — Une duplication du couple `ANACK` + `ORNUM` DOIT entraîner une erreur bloquante.
- **TEC-081** — Un template vide ou comportant une anomalie de balisage ou de clé définie ci-dessus DOIT entraîner une non-conformité `INVALID_TEMPLATE` et le code `1`. Une erreur de lecture du fichier ou un encodage UTF-8 invalide DOIT entraîner le code technique `2`.
- **TEC-082** — Chaque clé ANACK DOIT apparaître au plus une fois dans le template; une répétition DOIT produire `DUPLICATE_TEMPLATE_ANACK` et le code `1`.
- **TEC-083** — Les marqueurs ANACK du template sont des emplacements de substitution : le marqueur et sa valeur sont retirés à la composition et remplacés par les résumés et liens associés. En l'absence de document associé, le marqueur est retiré et l'emplacement reste vide.

## 7. Composition Markdown

La composition est effectuée par une fonction pure recevant le contenu du template, les documents validés et classés et le chemin de destination du Markdown. Elle retourne le Markdown complet sans écrire de fichier.

- **TEC-036** — Chaque document DOIT donner lieu à l'insertion de son résumé et d'un lien vers le PDF source.
- **TEC-037** — Les liens DOIVENT être calculés relativement au répertoire du Markdown final.
- **TEC-038** — Les caractères particuliers des chemins DOIVENT être correctement échappés ou encodés pour produire des liens Markdown valides.
- **TEC-039** — Les sauts de ligne internes d'`EXSUM` DOIVENT être conservés dans le Markdown généré.
- **TEC-084** — Le compositeur DOIT échapper le contenu d'EXSUM selon la syntaxe Markdown afin qu'il soit rendu comme texte littéral et ne puisse créer de titres, listes, liens, images, blocs HTML ou autres éléments Markdown actifs.
- **TEC-085** — Le rendu HTML DOIT échapper les caractères HTML du texte des résumés. Le HTML brut fourni par le template NE DOIT PAS être exécuté ni interprété comme contenu actif.
- **TEC-086** — La politique de ressources du template est restrictive : aucune ressource réseau ni ressource locale référencée par le Markdown (image, feuille de style, police ou autre ressource) ne DOIT être chargée. Les hyperliens, y compris les liens relatifs vers les PDF source, peuvent être conservés comme liens, mais ne sont jamais dereférencés par le moteur de rendu. Seules les ressources livrées avec l'application sont utilisables par le rendu.

## 8. Génération du PDF final

Chaîne retenue : **Markdown → markdown-it-py → HTML + CSS → WeasyPrint → PDF**.

- **TEC-040** — `markdown-it-py` DOIT assurer la conversion Markdown vers HTML.
- **TEC-041** — WeasyPrint DOIT assurer la génération du PDF à partir du HTML.
- **TEC-042** — Une feuille CSS embarquée DOIT définir la présentation du PDF.
- **TEC-043** — Le document final DOIT être au format A4, avec des marges périphériques de 2 cm.
- **TEC-044** — Les liens vers les PDF source DOIVENT être présents et exploitables dans le PDF final.
- **TEC-045** — Les sauts de ligne internes des résumés DOIVENT être restitués dans le PDF indépendamment du repli ordinaire des lignes Markdown.
- **TEC-087** — Les polices utilisées pour le rendu DOIVENT être livrées avec l'application, licenciées pour cet usage et explicitement sélectionnées par la feuille CSS. Le rendu NE DOIT PAS dépendre d'une substitution de police système.

- **TEC-097** — La feuille de style de référence est `src/ack_doc/resources/pdf.css`. Elle NE DOIT contenir ni `@import`, ni URL réseau, ni nom de police système.
- **TEC-098** — Le HTML de chaque document inséré DOIT avoir la structure suivante, générée par `composer.py` / `renderer.py` (et non par `markdown-it-py`) :

```html
<section class="ack-entry">
  <div class="ack-summary">résumé échappé, sauts de ligne conservés</div>
  <div class="ack-link-bubble"><p><a href="chemin/relatif.pdf">…</a></p></div>
</section>
```

  Cette structure est provisoire : elle sera alignée sur `page_setting_template.html` (modèle de mise en page, non finalisé) quand celui-ci sera terminé. Les classes `ack-entry`, `ack-summary`, `ack-link-bubble`, `ack-intro` et `ack-intro-text` sont le contrat entre le HTML et `pdf.css`.
- **TEC-108** — Le propos introductif d'une section est rédigé dans le template Markdown, entre deux lignes de marqueurs `<!-- ack:intro:start -->` et `<!-- ack:intro:end -->`, chacune seule sur sa ligne. Le texte compris entre les marqueurs est du Markdown ordinaire. Le renderer le convertit en `<section class="ack-intro"><div class="ack-intro-text">…</div></section>`. Les marqueurs ne peuvent être ni imbriqués ni non fermés : toute anomalie produit `INVALID_TEMPLATE` (code `1`). Ils ne sont reconnus que dans le template ; le contenu des résumés étant échappé (TEC-084), il ne peut pas en produire.
- **TEC-109** — Dans `pdf.css`, le propos introductif est en gris clair (`#6B7785`) sans retrait ; le résumé (`.ack-summary`) est en retrait (0,8 cm), en gris soutenu (`#1E2A36`) avec un filet vertical à gauche.

Exemple de section de template :

```markdown
## Dossier technique

<!-- ack:intro:start -->
Propos introductif de la section.
<!-- ack:intro:end -->

[[ANACK]]ACK0130[[/ANACK]]
```
- **TEC-099** — Les dimensions dans `pdf.css` DOIVENT être exprimées en unités d'impression (`pt`, `cm`), non en `px`.
- **TEC-100** — Chaque page DOIT porter en bas une numérotation « page / total » produite par `@page` (`counter(page)`, `counter(pages)`).
- **TEC-101** — Les `@font-face` DOIVENT déclarer les familles `ACK Sans` (Noto Sans : Regular, Italic, Bold, BoldItalic) et `ACK Mono` (Noto Sans Mono : Regular, Bold), à partir de fichiers **statiques** (TTF) situés dans `src/ack_doc/resources/fonts/`, chemins relatifs à `pdf.css`. Les polices variables sont exclues.
- **TEC-102** — La licence SIL OFL 1.1 des polices (`OFL.txt`) DOIT être livrée avec elles ; les empreintes SHA-256 des fichiers de polices DOIVENT être consignées dans le dépôt et vérifiées par un test.
- **TEC-103** — `renderer.py` DOIT appeler WeasyPrint avec `base_url` pointant vers le dossier `resources/` et un `FontConfiguration`. Le `url_fetcher` DOIT refuser toute URL qui n'est pas un fichier situé sous `resources/` (cohérent avec TEC-073 et TEC-086).
- **TEC-104** — Un fichier `src/ack_doc/resources/fonts.conf` DOIT limiter fontconfig au seul dossier `resources/fonts/`. `renderer.py` DOIT définir `FONTCONFIG_FILE` vers ce fichier avant toute initialisation de WeasyPrint, en générant si nécessaire un fichier temporaire dont le chemin du dossier de polices est absolu. Le cache fontconfig NE DOIT PAS être écrit dans le dépôt.
- **TEC-105** — Aucune police de repli système n'est autorisée. Les caractères absents de Noto Sans sont hors périmètre garanti ; leur affichage fait l'objet d'un test de non-régression documenté.
- **TEC-106** — Les fichiers `resources/pdf.css`, `resources/fonts.conf` et `resources/fonts/*` DOIVENT être inclus dans les données du paquet (`pyproject.toml`, cf. TEC-065).
- **TEC-107** — Un test DOIT vérifier, sur un PDF généré, que toutes les polices intégrées sont `NotoSans*` ou `NotoSansMono*` (par exemple `page.get_fonts()` de PyMuPDF), qu'elles sont embarquées, et que le numéro de page est présent.

Extrait de la feuille de référence (voir `pdf.css` pour la version complète) :

```css
@page {
    size: A4;
    margin: 2cm;
}

body {
    font-family: "ACK Sans";
    font-size: 11pt;
    line-height: 1.45;
}

.ack-summary {
    overflow-wrap: anywhere;
    margin-left: 0.8cm;
    padding-left: 8pt;
    border-left: 2pt solid #9BAFC1;
    color: #1E2A36;
}

.ack-intro-text {
    color: #6B7785;
}
```

Le contenu des résumés doit être échappé lors de la conversion HTML pour éviter que `<` ou `&` soient interprétés comme du balisage HTML.

## 9. Journal JSON

Le journal est produit par `journal.py` avec le module standard `json`.

- **TEC-046** — Le journal DOIT être un fichier JSON valide encodé en UTF-8.
- **TEC-047** — Il DOIT contenir la version du schéma, la version de l'application, la date et l'heure de début, la durée totale et les statistiques de traitement.
- **TEC-048** — Chaque PDF découvert DOIT disposer d'une entrée individuelle indiquant son chemin relatif, son statut et ses anomalies.
- **TEC-049** — Chaque anomalie DOIT comporter un code stable, un message et, si disponibles, la balise et la page concernées.
- **TEC-050** — Les documents conformes DOIVENT être représentés par `conforme` et une liste d'erreurs vide.
- **TEC-095** — Le statut global du journal DOIT être `success` pour une exécution réussie, `validation_failed` pour une non-conformité bloquante (code `1`) et `execution_failed` pour une erreur technique ou d'exécution (code `2`). Les statuts individuels des PDF sont `conforme` et `non_conforme`.

### 9.1 Exemple de journal

```json
{
  "schema_version": "1.0",
  "application_version": "1.0.0",
  "started_at": "2026-10-08T09:00:00+02:00",
  "duration_seconds": 3.42,
  "status": "validation_failed",
  "pdf_count": 2,
  "valid_count": 1,
  "invalid_count": 1,
  "files": [
    {
      "path": "dossier/doc1.pdf",
      "status": "conforme",
      "errors": []
    },
    {
      "path": "dossier/doc2.pdf",
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

### 9.2 Catalogue initial des erreurs

| Code | Signification |
|---|---|
| `MISSING_TAG` | Balise obligatoire absente |
| `DUPLICATE_TAG` | Balise présente plusieurs fois |
| `UNCLOSED_TAG` | Balise ouverte non fermée |
| `UNMATCHED_CLOSING_TAG` | Fermeture sans ouverture |
| `MALFORMED_TAG` | Syntaxe incorrecte |
| `NESTED_TAG` | Balises imbriquées |
| `INVALID_ANACK` | Clé analytique invalide |
| `INVALID_ORNUM` | Numéro d'ordre invalide |
| `INVALID_EXSUM` | Résumé invalide |
| `DUPLICATE_ANACK_ORNUM` | Couple clé/ordre dupliqué |
| `ANACK_NOT_IN_TEMPLATE` | Clé absente du modèle |
| `PDF_UNREADABLE` | PDF impossible à lire |
| `PDF_NO_TEXT` | PDF sans texte exploitable |
| `OUTPUT_EXISTS` | Fichier de sortie existant |
| `INVALID_TEMPLATE` | Template vide ou structure non conforme |
| `DUPLICATE_TEMPLATE_ANACK` | Clé ANACK répétée dans le template |
| `NO_PDF_FOUND` | Aucun PDF découvert dans le répertoire d'entrée |
| `EXSUM_CROSSES_PAGE` | Résumé EXSUM réparti sur plusieurs pages |
| `INPUT_DIR_ERROR` | Répertoire d'entrée inexistant ou inaccessible (code `2`) |
| `TEMPLATE_READ_ERROR` | Template inexistant ou illisible (code `2`) |
| `TEMPLATE_ENCODING_ERROR` | Template non encodé en UTF-8 valide (code `2`) |
| `OUTPUT_DIR_ERROR` | Répertoire de sortie inexistant ou inaccessible (code `2`) |
| `JOURNAL_DIR_ERROR` | Répertoire du journal inexistant ou inaccessible (code `2`) |
| `PATH_COLLISION` | Collision destructrice entre chemins de fichiers (code `2`) |
| `IO_ERROR` | Erreur d'accès ou d'écriture de fichier (code `2`) |
| `RENDER_ERROR` | Échec de la génération du PDF (code `2`) |
| `INTERNAL_ERROR` | Erreur interne (code `2`) |

Les anomalies qui ne concernent aucun PDF particulier (template, `NO_PDF_FOUND`, `OUTPUT_EXISTS`, erreurs techniques) sont consignées dans la liste `errors` de premier niveau du journal, ajoutée au schéma `1.0` de façon rétrocompatible.

Le catalogue est centralisé dans `errors.py`. Les codes publiés ne doivent pas être renommés sans évolution de version du schéma.

## 10. Gestion des erreurs et codes retour

| Code retour | Situation | Génération |
|---|---|---|
| `0` | Validation et génération réussies | Réalisée |
| `1` | Non-conformité d'une source PDF ou du contenu du template | Interdite |
| `2` | Erreur technique ou d'exécution | Interdite ou interrompue |

- **TEC-051** — L'application DOIT distinguer erreurs documentaires et erreurs techniques. Les PDF illisibles, corrompus ou sans texte exploitable sont des non-conformités documentaires (code `1`); les défaillances du moteur ou de l'application sont des erreurs techniques (code `2`).
- **TEC-052** — Les anomalies de balisage, de contenu, d'unicité et de correspondance avec le template, ainsi que les non-conformités du contenu du template, DOIVENT entraîner le code `1`.
- **TEC-053** — Les erreurs d'accès aux répertoires, de lecture du template, d'encodage du template, d'écriture et les exceptions techniques non récupérables DOIVENT entraîner le code `2`.
- **TEC-054** — Un document non conforme NE DOIT PAS empêcher l'analyse des autres documents lorsqu'une poursuite sûre reste possible.
- **TEC-055** — Le journal DOIT être produit même en cas de non-conformité, sous réserve que sa destination soit accessible.
- **TEC-088** — Un répertoire d'entrée accessible ne contenant aucun PDF DOIT être signalé par `NO_PDF_FOUND` et entraîner le code `1`.

## 11. Gestion des fichiers et écritures

- **TEC-056** — L'application DOIT vérifier l'existence des fichiers Markdown et PDF cibles avant la génération.
- **TEC-057** — Aucun fichier de sortie Markdown ou PDF existant NE DOIT être écrasé.
- **TEC-058** — Le Markdown et le PDF DOIVENT être générés dans des fichiers temporaires, idéalement sur le même système de fichiers que leur destination.
- **TEC-059** — Les fichiers temporaires DOIVENT être vérifiés avant leur publication.
- **TEC-060** — Une erreur de génération DOIT entraîner le nettoyage des fichiers temporaires.
- **TEC-061** — Les fichiers définitifs NE DOIVENT être publiés qu'après réussite des deux générations.
- **TEC-062** — La publication DOIT refuser de remplacer un fichier apparu entre la vérification initiale et l'écriture finale.
- **TEC-089** — Les fichiers PDF et Markdown de sortie NE DOIVENT PAS être écrasés. Un journal existant, en revanche, DOIT être remplacé à chaque exécution, y compris lorsque la validation échoue.
- **TEC-090** — Les répertoires parents de sortie inexistants NE DOIVENT PAS être créés implicitement; leur absence entraîne le code `2`.
- **TEC-091** — Les chemins relatifs des arguments `--input`, `--template`, `--output` et `--journal` sont résolus depuis le répertoire courant au lancement de la commande.
- **TEC-092** — Les liens vers les sources sont calculés depuis le répertoire contenant le Markdown généré. Le chemin relatif d'un PDF découvert et les chemins inscrits au journal sont exprimés depuis la racine `--input`.
- **TEC-093** — Les chemins normalisés des fichiers d'entrée, du template, du journal et des sorties DOIVENT être contrôlés afin d'éviter les collisions destructrices. Le journal ne peut désigner aucun PDF source, le template ni l'un des fichiers de sortie; les chemins PDF et Markdown de sortie doivent être distincts et ne peuvent désigner un fichier d'entrée ou le template.
- **TEC-096** — La présence préalable d'un fichier PDF ou Markdown de sortie DOIT produire `OUTPUT_EXISTS` et le code retour `2`; aucun fichier existant ne doit être modifié.

**Précision :** le renommage atomique d'un fichier ne rend pas atomique la publication de deux fichiers. L'implémentation doit prévoir une compensation si la publication du premier réussit et celle du second échoue, sans supprimer de fichiers préexistants.

## 12. Installation et déploiement

La solution est distribuée exclusivement sous forme d'**image Docker** à usage interne à l'organisation. Le code reste un paquet Python (`pyproject.toml`), installé dans l'image.

- **TEC-063** — Le projet DOIT comporter `pyproject.toml`.
- **TEC-064** — Les dépendances directes et transitives DOIVENT être verrouillées.
- **TEC-065** — Les ressources CSS et les polices DOIVENT être livrées avec l'application.
- **TEC-066** — L'application DOIT pouvoir être exécutée sans accès réseau après construction de l'image.
- **TEC-067** — Les bibliothèques système requises par WeasyPrint DOIVENT être installées dans l'image et listées dans le `Dockerfile` et le `README.md`.

### 12.0 Distribution par Docker

- **TEC-108** — Le dépôt DOIT comporter un `Dockerfile` construisant une image à partir d'une image de base Debian 13 (par exemple `python:3.13-slim-trixie`), dont la version est figée. Les paquets Python sont installés depuis `requirements.lock` (TEC-064), les paquets système depuis les dépôts Debian.
- **TEC-109** — L'image DOIT définir `ack-doc` comme `ENTRYPOINT`, de sorte que `docker run … <image> --input … --output …` utilise les mêmes arguments que la commande `ack-doc`.
- **TEC-110** — La construction DOIT être la seule étape nécessitant un accès réseau. L'exécution DOIT fonctionner avec `--network none`.
- **TEC-111** — Le conteneur NE DOIT PAS s'exécuter en root par défaut : l'image définit un utilisateur non privilégié, et le script d'enveloppe passe `--user` avec l'UID et le GID de l'appelant afin que les fichiers produits appartiennent à l'utilisateur.
- **TEC-112** — Les entrées, le template et les sorties DOIVENT se trouver sous un même point de montage (`/work`, répertoire de travail du conteneur). Les chemins relatifs sont donc résolus depuis `/work` (TEC-091), et les liens du Markdown vers les PDF source restent valides sur l'hôte (TEC-092). Les chemins hors de `/work` sont refusés par le script d'enveloppe.
- **TEC-113** — Le code de sortie du conteneur DOIT être celui de `ack-doc` (`0`, `1` ou `2`) ; le script d'enveloppe le renvoie sans le modifier. Un échec de Docker lui-même (démon absent, image introuvable) DOIT être signalé distinctement, avec le code `2`.
- **TEC-114** — Un script `ack-doc.sh` DOIT être fourni. Il vérifie la présence de Docker, monte le répertoire courant sur `/work`, lance l'image avec `--rm`, `--network none` et `--user`, puis transmet les arguments.
- **TEC-115** — L'image DOIT fonctionner avec un système de fichiers racine en lecture seule (`--read-only`) : les caches (fontconfig, `XDG_CACHE_HOME`) et les fichiers temporaires sont dirigés vers `/tmp` (`--tmpfs /tmp`). Les fichiers temporaires de publication (TEC-060 à TEC-062) sont créés dans le répertoire de sortie.
- **TEC-116** — L'image DOIT porter une étiquette de version (tag) correspondant à celle du paquet, et ne DOIT pas être publiée hors de l'organisation (registre interne ou export par `docker save`).
- **TEC-117** — Un test d'intégration DOIT lancer l'image construite sur le corpus de non-régression, avec `--network none` et `--read-only`, et vérifier les codes retour, la propriété des fichiers produits et les polices du PDF (TEC-107).
- **TEC-118** — Les licences des composants (dont PyMuPDF) ne constituent pas une contrainte pour cette distribution interne. Toute diffusion de l'image hors de l'organisation DOIT faire l'objet d'une nouvelle analyse de licence préalable.

### 12.1 Arborescence du projet

```text
ACK-DOC/
├── pyproject.toml
├── README.md
├── requirements.lock
├── Dockerfile
├── ack-doc.sh
├── src/
│   └── ack_doc/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── discovery.py
│       ├── pdf_reader.py
│       ├── tag_parser.py
│       ├── validators.py
│       ├── template.py
│       ├── models.py
│       ├── composer.py
│       ├── renderer.py
│       ├── journal.py
│       ├── errors.py
│       └── resources/
│           ├── pdf.css
│           ├── fonts.conf
│           └── fonts/
│               ├── OFL.txt
│               ├── NotoSans-Regular.ttf
│               ├── NotoSans-Italic.ttf
│               ├── NotoSans-Bold.ttf
│               ├── NotoSans-BoldItalic.ttf
│               ├── NotoSansMono-Regular.ttf
│               └── NotoSansMono-Bold.ttf
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── fixtures/
└── docs/
    ├── specification_fonctionnelle.md
    └── specification_technique.md
```

Le point d'entrée expose la commande `ack-doc`, exécutée dans l'image Docker (TEC-109) ; `ack-doc.sh` est le lanceur côté hôte (TEC-114).

## 13. Stratégie de tests

Le framework retenu est **pytest**.

### 13.1 Tests unitaires

Vérification de l'analyse des balises, de la normalisation, de la validation des contenus, du classement, des chemins relatifs et de la composition Markdown. Ces tests ne nécessitent pas de PDF, sauf pour les fonctions d'extraction.

### 13.2 Tests d'intégration

De vrais PDF vérifient toute la chaîne, depuis la découverte jusqu'aux sorties. Ils couvrent les cas T001 à T062 de la spécification fonctionnelle.

### 13.3 Tests de non-régression

Le corpus de référence comprend des PDF provenant de plusieurs générateurs (dont Adobe Acrobat et l'impression virtuelle PDF), d'applications métier et de structures internes variées de couche texte. Il comprend des exemples conformes et des cas d'altérations couvertes par la présente spécification; pour chaque fichier, les valeurs attendues, pages concernées et anomalies attendues sont consignées dans les fixtures de test. La vérification automatisée porte au minimum sur l'ouverture du PDF généré, son nombre de pages, son texte extrait, ses dimensions de page et ses liens. Une comparaison pixel à pixel n'est pas exigée.

- **TEC-068** — Chaque nouvelle version de PyMuPDF DOIT être validée sur le corpus de non-régression avant adoption.
- **TEC-069** — Chaque modification du moteur de génération DOIT faire l'objet d'une vérification du rendu PDF.
- **TEC-070** — Les tests automatisés DOIVENT être exécutés avant toute livraison.
- **TEC-094** — Les mises à jour de bibliothèques d'extraction ou de génération DOIVENT être vérifiées sur l'ensemble du corpus de référence; les écarts attendus et acceptés DOIVENT être documentés dans les tests, et toute régression des valeurs extraites, des liens ou de la géométrie de page DOIT faire échouer la validation.

## 14. Sécurité et robustesse

Les PDF et les résumés sont considérés comme des données d'entrée non fiables.

- **TEC-071** — L'application NE DOIT PAS exécuter de commandes ou scripts provenant du contenu des PDF.
- **TEC-072** — Les contenus `EXSUM` DOIVENT être échappés lors de leur insertion dans le HTML et ne doivent pas être interprétés comme du HTML actif.
- **TEC-073** — La conversion HTML vers PDF NE DOIT PAS autoriser d'accès réseau non nécessaire.
- **TEC-074** — Les chemins relatifs DOIVENT être normalisés et vérifiés avant utilisation.
- **TEC-075** — Les exceptions techniques DOIVENT être interceptées au niveau de l'orchestrateur avec message et code retour appropriés.

## 15. Critères de conformité de la conception

Le développement est considéré conforme lorsque :

1. L'architecture modulaire est respectée.
2. PyMuPDF est le moteur unique d'extraction.
3. L'analyseur détecte les anomalies définies.
4. Les données sont représentées par des structures typées.
5. La validation est terminée avant toute génération.
6. La composition Markdown est indépendante de la lecture PDF.
7. La génération PDF utilise `markdown-it-py` et WeasyPrint.
8. Les sauts de ligne des résumés sont préservés.
9. Les liens relatifs fonctionnent dans le Markdown et le PDF.
10. Le journal JSON respecte son schéma versionné.
11. Les sorties Markdown/PDF existantes ne sont jamais écrasées; le journal existant est remplacé conformément à la règle définie.
12. Les erreurs entraînent les codes retour prévus.
13. Les tests unitaires, d'intégration et de non-régression réussissent.
14. Le logiciel fonctionne sous Debian 13 dans son environnement Python isolé.

## 16. Décisions complémentaires à figer

| Sujet | Proposition de conception | Statut |
|---|---|---|
| ANACK dupliqué dans le template | Non-conformité bloquante du template, code `1` | Retenu |
| EXSUM traversant deux pages PDF | Non-conformité bloquante; les résumés doivent tenir sur une seule page | Retenu |
| Résumé inséré | Texte suivi de `[Document source](chemin)`; un saut de ligne sépare les documents insérés | Retenu |
| Markdown contenant des sauts de ligne | Préservation explicite dans le HTML/PDF | Retenu techniquement |
| PDF illisible ou corrompu | Non-conformité de source, code `1`; panne du moteur, code `2` | Retenu |
| Absence totale de PDF dans `--input` | Erreur bloquante, code `1` | Retenu |
| Fichier journal déjà existant | Remplacement du journal autorisé; les sorties Markdown/PDF restent protégées | Retenu |
| Ressources externes dans le Markdown | Aucune ressource réseau ou locale référencée n'est chargée; les hyperliens restent des liens | Retenu |

## Conclusion

Cette spécification définit les modules à développer, leurs responsabilités, les structures de données, les bibliothèques, les contrôles, les mécanismes d'écriture, les erreurs et les obligations de test. Les décisions complémentaires du chapitre 16 sont retenues et intégrées aux exigences applicables.
