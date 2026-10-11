# ACK-DOC

Valide des PDF balisés (`ANACK`, `ORNUM`, `EXSUM`), compose un récapitulatif Markdown à partir d'un modèle, le rend en PDF (markdown-it-py + WeasyPrint, police Noto Sans embarquée) et écrit un journal JSON. Spécifications : `specifications/`.

## Installation (Docker)

```bash
docker build -t ack-doc:1.0.0 .
```

Bibliothèques système installées dans l'image : `libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0`.

## Utilisation

Depuis le répertoire contenant les données (tous les chemins doivent être sous ce répertoire) :

```bash
./ack-doc.sh --input ./documents --template ./template.md \
             --output ./resultats/ack-doc.pdf --journal ./resultats/ack-doc.json
```

Le Markdown généré est écrit à côté du PDF (`ack-doc.md`). Codes retour : `0` succès, `1` non-conformité (rien n'est généré), `2` erreur technique. Les fichiers de sortie existants ne sont jamais écrasés ; le journal est remplacé.

## Développement et tests

```bash
uv venv && uv pip install -e ".[dev]"
pytest
```

Le test de rendu réel est ignoré si WeasyPrint/Pango est indisponible (Windows par exemple) ; il s'exécute sous Linux ou dans l'image.

`requirements.lock` se régénère avec :
`uv pip compile pyproject.toml --python-platform linux --python-version 3.13 -o requirements.lock`.
