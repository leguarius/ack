#!/usr/bin/env bash
# Installation automatisée d'ACK-DOC sur Debian 13 : Docker, git, clonage GitHub, image, commande.
# Usage : ACK_DOC_REPO=https://github.com/<organisation>/<depot>.git ./install.sh [--ref <tag|branche>]
set -euo pipefail

REPO="${ACK_DOC_REPO:-}"
REF="main"
SRC="${ACK_DOC_SRC:-$HOME/ack-doc}"

while [ $# -gt 0 ]; do
    case "$1" in
        --ref) REF="${2:?--ref attend une valeur}"; shift 2 ;;
        *) echo "Argument inconnu : $1" >&2; exit 2 ;;
    esac
done

if [ -z "$REPO" ]; then
    echo "Définissez ACK_DOC_REPO avec l'URL du dépôt GitHub." >&2
    exit 2
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null || { echo "sudo est requis." >&2; exit 2; }
    SUDO="sudo"
fi

echo "==> Installation de git et Docker"
$SUDO apt-get update
$SUDO apt-get install -y --no-install-recommends git ca-certificates docker.io
$SUDO systemctl enable --now docker

echo "==> Récupération du projet ($REPO, $REF) dans $SRC"
if [ -d "$SRC/.git" ]; then
    git -C "$SRC" fetch --tags origin
    git -C "$SRC" checkout "$REF"
    git -C "$SRC" pull --ff-only origin "$REF" 2>/dev/null || true
else
    git clone "$REPO" "$SRC"
    git -C "$SRC" checkout "$REF"
fi

cd "$SRC"
sed -i 's/\r$//' ack-doc.sh
VERSION="$(sed -n 's/^VERSION="\(.*\)"/\1/p' ack-doc.sh)"

echo "==> Construction de l'image ack-doc:$VERSION"
$SUDO docker build -t "ack-doc:$VERSION" .

echo "==> Installation de la commande ack-doc"
$SUDO install -m 755 ack-doc.sh /usr/local/bin/ack-doc

if [ "$(id -u)" -ne 0 ] && ! id -nG "$USER" | grep -qw docker; then
    $SUDO usermod -aG docker "$USER"
    echo "Utilisateur $USER ajouté au groupe docker : fermez puis rouvrez votre session."
fi

echo "==> Terminé. Vérification : ack-doc --version"
