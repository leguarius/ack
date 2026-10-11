# Analyse des métadonnées GED des PDF

Corpus : 11 PDF du répertoire `doc\metadata`. Priorité des champs : Document ID, Version, Document No, Titre. La date de mise en vigueur est ignorée.

| Fichier | Document ID | Version | Document No | Titre |
|---|---|---|---|---|
| BER011_Celsite Implantofix Implant.pdf | — (non signé) | — | — | — |
| BER034_10F pusher.pdf | — (non signé) | — | — | — |
| Celsite extra small size - Clinical Strategy - PRO169 (5).pdf | BB-RECHA-008341 | 1.0 | PRO N°169 | Celsite extra small size - Clinical Strategy - PRO169 |
| Comparatif HCT COT DM A1078.xlsx.pdf | BB-RECHA-014620 | 0.7 | Comparatif HCT COT DM A1078 (libellé « Référence ») | **introuvable** |
| EF294 Scellage Alveole Vide - Breather Bag MDR.pdf | BB-RECHA-007610 | 2.0 | EF294 Ed01 -I-02 | EF294 Scellage Alveole Vide - Breather Bag MDR |
| EF297 Prepa Conditionnement Primaire Echantillons MDR Hors Vision.pdf | BB-RECHA-007797 | 2.0 | EF297Ed01 -I-02 | EF297 Prepa Conditionnement Primaire Echantillons MDR Hors Vision |
| INJECTION_BAGUE_A1237_PVA0586_QO.pdf | OQ-RECHA-000124 | 1.0 | PVA0586_QO_01 | INJECTION_BAGUE_A1237_PVA0586_QO |
| PRM013_Report_Surecan safety II non-coring needle (2).pdf | BB-RECHA-004938 | 2.0 | PRM013 Ed10 | PRM013_Report_Surecan safety II non-coring needle |
| PRO0170-20261002-Données d'entrée conception alvéole.pdf | BB-RECHA-014618 | 0.6 | **NA** (libellé « Référence ») | **introuvable** |
| PSP433_01_Sealing.pdf | BB-RECHA-014298 | 1.0 | PSP433_01 | PSP433_01_Sealing |
| PVA0765_OQ_Automated supplier detergent cleaning_CFN014_01.pdf | OQ-RECHA-000266 | 1.0 | PVA0765_OQ_01 | PVA0765_OQ_Automated supplier detergent cleaning_CFN014_01 |

## Observations

- **Nature des données** : texte ajouté sur les pages (bandeau de pied de page, page de signature), et non des champs de métadonnées PDF.
- **Document ID** : format strict `^(BB|OQ)-RECHA-\d{6}$`, identique sur toutes les pages d'un document.
- **Version** : `chiffre.chiffre` (0.6, 0.7, 1.0, 2.0).
- **Document No** : format libre (espaces, `°`, `NA`). À lire en entier, entre « Document No.: » (ou « Référence: ») et « - Version », sans normalisation.
- **Titre** :
  - présent sur la page de signature (« Title: … Initiator: ») pour 7 documents ; PVA0765 le porte aussi dans le bandeau ;
  - absent pour Comparatif et PRO0170, dont le bandeau utilise « Référence » et qui n'ont ni « Initiator » ni ligne « Title ».
- **BER011 et BER034** : documents non signés, sans données GED (ni bandeau, ni page de signature).

## Décision en attente : titre absent

1. Déclarer le document non conforme (option la plus stricte).
2. Repli sur Document No (inutilisable pour PRO0170 : `NA`).
3. Repli sur le nom du fichier sans extension.
