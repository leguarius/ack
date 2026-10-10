# Rapport de revue — Spécifications ACK-DOC

**Objet :** Revue des spécifications fonctionnelle (v1.0) et technique de conception (ACK-DOC-ST-001 v1.0) de l'application ACK-DOC
**Objectif de la revue :** déterminer si les spécifications sont correctes, suffisantes et non ambiguës avant l'activité de conception
**Verdict global :** **REVUE AVEC RÉSERVES** — les spécifications sont de bonne qualité et largement actionnables, mais **elles ne peuvent pas être gelées en l'état** : une contradiction majeure sur les codes retour, huit décisions non arbitrées (chapitre 16 de la spéc. technique) et plusieurs zones d'ombre doivent être levées avant de figer la conception et les tests d'acceptation.

---

## 1. Synthèse

| Critère de revue | Appréciation |
|---|---|
| Couverture fonctionnelle des besoins | ✅ Bonne — périmètre, phases, sorties et codes retour définis |
| Cohérence entre spéc. fonctionnelle et technique | ⚠️ Une contradiction majeure (PDF corrompu, code 1 vs 2) et divergences de vocabulaire |
| Non-ambiguïté des règles de validation | ⚠️ Bonne pour ANACK/ORNUM ; imprécisions sur EXSUM et la normalisation |
| Complétude | ❌ 8 décisions « à confirmer », règles de validation du template non définies |
| Testabilité | ✅ Bonne — matrice T001–T062 exhaustive, exigences TEC numérotées |
| Adéquation des choix techniques | ✅ Crédible (PyMuPDF, markdown-it-py, WeasyPrint, pytest) |

---

## 2. Points forts

1. **Séparation validation / génération** clairement imposée (fonctionnelle §14, TEC-003/004), avec la règle « une seule erreur interdit toute génération » non ambiguë.
2. **Matrice de tests T001–T062** exceptionnellement complète, couvrant chaque règle avec un résultat attendu et un caractère bloquant. C'est un socle d'acceptation directement exploitable.
3. **Catalogue d'erreurs stable et structuré** (codes `MISSING_TAG`, `INVALID_ANACK`, etc.) avec exigence de versionnement du schéma du journal.
4. **Architecture modulaire** aux responsabilités délimitées, composition Markdown testable indépendamment de l'extraction PDF (TEC-010/026), ce qui est la bonne décision.
5. **Prise en compte de la sécurité** : contenus PDF considérés comme non fiables, échappement HTML, interdiction de l'OCR et de l'accès réseau.
6. **Gestion des écritures** réfléchie (fichiers temporaires, publication en deux temps, compensation, TEC-056 à TEC-062), y compris la lucidité sur la non-atomicité de la publication double.

---

## 3. Anomalies et ambiguïtés relevées

### 3.1 🔴 Critique — Contradiction sur la classification « PDF corrompu »

- **Spéc. fonctionnelle §18** classe explicitement « impossibilité de lire un PDF » et « PDF corrompu » parmi les **erreurs d'exécution → code retour 2**.
- **Spéc. technique §16** propose à l'inverse : « code `1` si document source non exploitable ; `2` si panne technique du moteur ».
- Ces deux positions sont incompatibles. Or ce point détermine le comportement des tests **T033, T053 et T057** et l'interprétation de `PDF_UNREADABLE` / `PDF_NO_TEXT` (code 1 ou 2 ?).

**Recommandation :** arbitrer formellement. La proposition du chapitre 16 est techniquement plus saine (distinguer « donnée source défectueuse » de « panne du moteur »), mais elle impose de **corriger la spécification fonctionnelle §18**. Tant que ce point n'est pas tranché, les codes retour ne sont pas spécifiés de manière vérifiable.

### 3.2 🔴 Critique — Huit décisions de conception non arbitrées (spéc. technique §16)

Le chapitre 16 liste huit sujets « à confirmer » qui sont pourtant **structurants** :

1. ANACK dupliqué dans le template — bloquant ou non ;
2. EXSUM traversant deux pages — comportement exact de la frontière de page ;
3. Format d'insertion du résumé et du lien source (séparation entre documents) ;
4. PDF corrompu (cf. 3.1) ;
5. Absence totale de PDF dans `--input` ;
6. Fichier journal déjà existant ;
7. Politique sur les ressources externes du Markdown ;
8. Politique de ressources locales.

**Recommandation :** la conception ne devrait pas démarrer sans un chapitre 16 entièrement « Retenu ». Chacun de ces points affecte soit le parseur, soit le compositeur, soit les tests d'acceptation.

### 3.3 🟠 Majeur — Règles de validation du template non définies

La TEC-029 exige que « le modèle DOIT être validé avant la validation croisée », mais **aucun critère de validité du template n'est spécifié** :

- marqueur `[[ANACK]]…[[/ANACK]]` mal formé dans le template : erreur ou ignoré ?
- valeur ne respectant pas `^ACK[0-9]{4}$` dans le template : bloquant ?
- encode UTF-8 invalide, fichier vide ?
- la duplication de clé ANACK dans le template est précisément l'un des points « à confirmer ».

Sans ces règles, les tests d'intégration sur le template ne peuvent pas être écrits de façon déterministe.

**Recommandation :** ajouter une section « Validation du modèle » listant les anomalies bloquantes du template (avec codes d'erreur dédiés, p.ex. `INVALID_TEMPLATE`, `DUPLICATE_TEMPLATE_ANACK`).

### 3.4 🟠 Majeur — Robustesse de la détection des balises face à l'extraction PDF

Les deux spécifications supposent que les marqueurs `[[ANACK]]`, `[[ORNUM]]`, `[[EXSUM]]` sont restitués intacts par l'extraction texte. Or, dans la réalité :

- un marqueur peut être **coupé par un retour à la ligne** ou par le « form feed » de fin de page (`[[EXSUM]\ntexte`);
- l'extraction PyMuPDF peut insérer des espaces ou réordonner les fragments selon la structure interne de la couche texte ;
- la césure ou le retrait de première ligne peut fragmenter un marqueur.

La spécification technique impose un séparateur explicite entre pages (bien), mais **ne spécifie pas** : (a) si les marqueurs peuvent s'étendre sur plusieurs lignes ; (b) comment normaliser les artefacts d'extraction avant l'analyse (suppression des retours à la ligne *dans les marqueurs* uniquement) ; (c) si une balise coupée doit être signalée comme `MALFORMED_TAG` ou tolérée.

**Recommandation :** spécifier explicitement : les marqueurs sont recherchés sur un texte où les sauts de ligne internes aux marqueurs sont tolérés (ou non), et documenter le comportement attendu pour `T023`/`T025`/`T026` dans le cas d'un marqueur fragmenté.

### 3.5 🟠 Majeur — Contenu EXSUM contenant de la syntaxe Markdown ou des marqueurs

TEC-072 impose l'échappement **HTML** des résumés, mais rien ne spécifie le traitement d'un EXSUM contenant :

- des caractères Markdown structurants (`#`, `*`, `[lien](…)`, `---`) qui seront **interprétés** par markdown-it-py et peuvent casser la structure du document final ;
- les chaînes `[[ANACK]]`, `[[EXSUM]]`… qui pollueraient le parseur du template/compositeur ;
- des caractères `<`, `>` (couverts par TEC-072 pour le HTML, mais pas pour le Markdown).

**Recommandation :** spécifier une politique d'échappement Markdown des résumés (par exemple échappement des caractères actifs) et l'inscription d'un test dédié dans la matrice (absent de T001–T062).

### 3.6 🟠 Majeur — Imprécisions sur la normalisation

- « Espaces périphériques » : la liste exacte des caractères supprimés n'est pas définie (espace simple, tabulation, sauts de ligne périphériques ? espace insécable ?). T019 dit « espaces périphériques supprimés » sans préciser si cela inclut les retours à la ligne en tête/queue d'EXSUM.
- EXSUM « ne doit pas commencer par ACK » : sensible à la casse ? `Ack…` est-il valide ? Et s'agit-il de la chaîne littérale `ACK` ou de toute valeur respectant `^ACK\d{4}$` (une validation plus logique, sinon `ACKNOWLEDGEMENTS…` serait refusé) ?
- Lettres accentées / Unicode dans EXSUM : « des lettres » — ASCII uniquement ou Unicode ? À expliciter pour les tests.

### 3.7 🟡 Mineur — Incohérences de vocabulaire entre les exemples de journal

- Fonctionnelle §17.3 : statut global `"error"`, statut fichier `"error"` ; technique §9.1 : `"validation_failed"` et `"non_conforme"`.
- Fonctionnelle §17.3 : date sans fuseau horaire ; technique : ISO 8601 avec offset.
- La fonctionnelle autorise a priori le complément du schéma, mais **un seul vocabulaire doit être déclaré normatif** (celui de la technique, plus complet) et les exemples alignés.

### 3.8 🟡 Mineur — Chemins relatifs : référentiel non explicité

« Chemin relatif » du journal, des liens et des arguments : relatif au **répertoire courant d'appel**, à `--input`, ou au répertoire du fichier de sortie ? L'exemple (`documents/doc1.pdf`) suggère le répertoire courant, mais ce n'est jamais énoncé. À expliciter pour T042/T043/T054.

### 3.9 🟡 Mineur — Divers points à clarifier

| # | Point | Question ouverte |
|---|---|---|
| 1 | `--output` : répertoire parent inexistant | Création automatique (avec quels parents ?) ou erreur code 2 ? |
| 2 | Journal existant | Écrasement autorisé ou `OUTPUT_EXISTS` ? (à confirmer §16) |
| 3 | `--input` vide de PDF | Bloquant ou succès avec section vide ? (à confirmer §16) |
| 4 | Reproductibilité (TEC-006) | WeasyPrint dépend des polices système : prévoir l'épinglage de polices pour un rendu reproductible sur des machines différentes |
| 5 | ANACK/ORNUM présents dans le template | Le marqueur du template doit-il être supprimé ou conservé en tête de section dans le document final ? Non spécifié |
| 6 | Balises avec casse incorrecte dans un PDF (`[[anack]]…`) | Erreur explicite « casse incorrecte » ou simplement `MISSING_TAG` + `MALFORMED_TAG` ? T007 attend « balise incorrecte » sans code précis |
| 7 | ORNUM = 0 | Trier « par ORNUM croissant » : le 0 vient-il avant 1 ? (implicite mais à confirmer) |
| 8 | Exemples JSON de la fonctionnelle §17.3 | Clôtures de blocs de code erronées (artefact probable) — à corriger dans le document source |

---

## 4. Évaluation de la testabilité

La matrice T001–T062 est le meilleur atout du dossier : chaque règle métier y est traçable. Réserves :

- **T033 / T053** ne sont pas exécutables de façon déterministe tant que la contradiction 3.1 n'est pas levée.
- Les **tests template** (T035–T037) ne couvrent pas les anomalies du template lui-même (cf. 3.3).
- Aucun test ne couvre un **EXSUM contenant des caractères Markdown/HTML** (cf. 3.5) ni un **marqueur fragmenté par l'extraction** (cf. 3.4).
- TEC-068/069 (corpus de non-régression, validation PyMuPDF) sont de bonnes exigences mais le corpus lui-même n'est pas spécifié (composition, taille, critères de validation du rendu PDF — comparaison visuelle ? métadonnées ? diff texte ?).

---

## 5. Recommandations priorisées

### Avant gel des spécifications (bloquant pour la conception)

1. **Arbitrer la contradiction code 1 / code 2 pour les PDF illisibles ou corrompus** et aligner la spécification fonctionnelle §18 avec la décision.
2. **Clore les huit décisions « à confirmer »** du chapitre 16 et les intégrer au corps normatif.
3. **Définir les règles de validation du template** (marqueurs mal formés, clés invalides, doublons) avec codes d'erreur dédiés.
4. **Spécifier le comportement face aux marqueurs fragmentés** par l'extraction PDF (retours à la ligne, frontières de page) et le traitement des frontières de page *à l'intérieur* d'un EXSUM.
5. **Spécifier l'échappement Markdown des résumés** (en complément de l'échappement HTML) et ajouter un test à la matrice.

### Avant/pendant la conception

6. Définir précisément la **normalisation** (caractères supprimés, portée du trim, casse de la règle « ne commence pas par ACK », Unicode admis dans EXSUM).
7. Harmoniser le **vocabulaire et le schéma du journal** (adopter le schéma technique §9.1 comme norme, corriger les exemples fonctionnels).
8. Expliciter le **référentiel des chemins relatifs** (répertoire courant d'appel recommandé) et le comportement pour un répertoire de sortie inexistant.
9. Préciser la politique de **polices embarquées** pour garantir la reproductibilité du PDF (TEC-006).
10. Décrire le **corpus de non-régression** et la méthode de vérification du rendu PDF (TEC-069).

---

## 6. Conclusion

Les spécifications ACK-DOC sont **au-dessus de la moyenne** : périmètre clair, deux phases impératives, matrice de tests exhaustive, catalogue d'erreurs versionné, architecture modulaire cohérente et exigences techniques numérotées et vérifiables.

Elles ne sont toutefois **pas encore gelables**. Trois chantiers bloquent le démarrage serein de la conception :

1. la **contradiction sur le code retour des PDF corrompus** (fonctionnelle vs technique) ;
2. les **huit décisions non arbitrées** du chapitre 16, qui touchent le parseur, le compositeur et les tests ;
3. l'absence de **règles de validation du template** et de **spécification du comportement face aux artefacts d'extraction PDF** (marqueurs fragmentés, EXSUM multipage, contenus Markdown actifs).

Une fois ces points corrigés — les recommandations §5.1 suffisent —, le dossier sera **suffisant et non ambigu** pour engager la conception détaillée puis le développement, la matrice T001–T062 servant directement de base de tests d'acceptation.