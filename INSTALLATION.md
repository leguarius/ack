# ACK-DOC — Installation et utilisation sur Debian 13

## 1. Installation automatique (recommandée)

Remplacez `<organisation>/<depot>` par l'adresse du dépôt GitHub d'ACK-DOC :

```bash
sudo apt update && sudo apt install -y curl
curl -fsSLO https://raw.githubusercontent.com/<organisation>/<depot>/main/install.sh
chmod +x install.sh
ACK_DOC_REPO=https://github.com/<organisation>/<depot>.git ./install.sh
```

Le script installe `git` et Docker, clone le projet dans `~/ack-doc` (ou le met à jour s'il existe déjà), construit l'image `ack-doc:<version>` et installe la commande `/usr/local/bin/ack-doc`. Pour installer une version précise : `./install.sh --ref v1.0.0` (tag ou branche). Le dossier d'installation se change avec `ACK_DOC_SRC=/chemin`.

Si c'est la première installation de Docker pour votre utilisateur, fermez puis rouvrez la session (appartenance au groupe `docker`). Vérifiez :

```bash
ack-doc --version
```

Résultat attendu : `ack-doc 1.0.0`.

Pour un dépôt privé : utilisez une clé SSH de déploiement (`ACK_DOC_REPO=git@github.com:<organisation>/<depot>.git`) ou un jeton d'accès, et copiez `install.sh` par un autre moyen que `curl`.

Un accès réseau n'est nécessaire que pour l'installation et la construction ; l'exécution se fait sans réseau.

## 2. Installation manuelle (équivalent)

```bash
sudo apt update
sudo apt install -y git docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"        # puis rouvrir la session

git clone https://github.com/<organisation>/<depot>.git ~/ack-doc
cd ~/ack-doc
git checkout v1.0.0                    # optionnel : version précise
sed -i 's/\r$//' ack-doc.sh
docker build -t ack-doc:1.0.0 .
sudo install -m 755 ack-doc.sh /usr/local/bin/ack-doc
```

## 3. Mise à jour

```bash
cd ~/ack-doc && git pull
```

puis relancer `install.sh` (il reconstruit l'image et réinstalle la commande), ou refaire les trois dernières commandes de l'installation manuelle.
## 4. Organiser les fichiers

**Règle essentielle :** l'application s'exécute dans un conteneur qui ne voit que le **répertoire courant** (où vous lancez la commande) et ses sous-répertoires. Tous les chemins passés en argument doivent se trouver sous ce répertoire ; sinon la commande refuse de s'exécuter (code 2).

Exemple d'arborescence de travail :

```
~/travail/
├── documents/          ← PDF à analyser
│   ├── dossier-A/
│   │   └── doc1.pdf
│   └── doc2.pdf
├── template.md         ← modèle Markdown
└── resultats/          ← répertoire de sortie (à créer)
```

- Les PDF sont recherchés **récursivement** sous le répertoire `--input` (extension `.pdf`, casse indifférente).
- Le répertoire de sortie et celui du journal doivent **exister** avant l'exécution (`mkdir -p resultats`).
- Les fichiers de sortie existants ne sont **jamais écrasés** : supprimez ou renommez les anciens. Seul le journal est remplacé à chaque exécution.
- Le modèle ne contient que des marqueurs `[[ANACK]]ACK0001[[/ANACK]]` (une clé par marqueur, sans doublon), placés là où les résumés doivent apparaître. Exemple :

```markdown
# Accusés de réception

## Lot 1

[[ANACK]]ACK0001[[/ANACK]]

## Lot 2

[[ANACK]]ACK0002[[/ANACK]]
```

- Chaque PDF source doit contenir, sur le texte du PDF (pas d'OCR), les balises `[[ANACK]]ACK0001[[/ANACK]]`, `[[ORNUM]]1[[/ORNUM]]` et `[[EXSUM]]résumé…[[/EXSUM]]` (EXSUM sur une seule page).

## 5. Lancer l'analyse

```bash
cd ~/travail
mkdir -p resultats
ack-doc --input ./documents --template ./template.md \
        --output ./resultats/ack-doc.pdf --journal ./resultats/ack-doc.json
```

Produits :

| Fichier | Contenu |
|---|---|
| `resultats/ack-doc.pdf` | PDF final |
| `resultats/ack-doc.md` | Markdown généré (même nom que le PDF) |
| `resultats/ack-doc.json` | Journal (toujours produit, y compris en cas d'erreur) |

Les liens vers les PDF sources dans le document sont relatifs à l'emplacement du Markdown : conservez l'arborescence `documents/` et `resultats/` côte à côte pour que les liens restent valides.

## 6. Codes retour

| Code | Signification |
|---|---|
| `0` | Succès : Markdown et PDF générés |
| `1` | Non-conformité (PDF, balises, modèle, aucun PDF trouvé) : rien n'est généré, voir le journal |
| `2` | Erreur technique (répertoire absent, sortie déjà existante, chemin hors du répertoire courant, Docker…) |

Consultez le journal pour le détail : `cat resultats/ack-doc.json` (statut global, et pour chaque PDF les anomalies avec code, balise et page).

## 7. Dépannage

| Symptôme | Cause probable |
|---|---|
| `permission denied` sur le socket Docker | Session non rouverte après `usermod`, ou utilisateur hors du groupe `docker` |
| `chemin hors du répertoire courant` | Placez-vous dans un répertoire parent de tous les fichiers manipulés |
| `/usr/bin/env: 'bash\r'` | Fins de ligne Windows : `sed -i 's/\r$//' ack-doc.sh` |
| `OUTPUT_EXISTS` (code 2) | Le PDF ou le Markdown de sortie existe déjà |
| `NO_PDF_FOUND` (code 1) | Aucun `.pdf` sous `--input` |
| Image introuvable | Reconstruire l'image, ou définir `ACK_DOC_IMAGE=<nom:tag>` |
