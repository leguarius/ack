#!/usr/bin/env bash
# Enveloppe Docker d'ACK-DOC (TEC-114). Les chemins doivent se situer sous le répertoire courant.
set -u

VERSION="1.0.0"
IMAGE="${ACK_DOC_IMAGE:-ack-doc:${VERSION}}"

if ! command -v docker >/dev/null 2>&1; then
    echo "ack-doc : Docker est introuvable." >&2
    exit 2
fi

root="$(pwd -P)"
args=()
expect_path=0
for arg in "$@"; do
    if [ "$expect_path" = 1 ]; then
        expect_path=0
        abs="$(realpath -m -- "$arg")"
        case "$abs" in
            "$root"|"$root"/*) ;;
            *) echo "ack-doc : chemin hors du répertoire courant : $arg" >&2; exit 2 ;;
        esac
        args+=("/work${abs#"$root"}")
        continue
    fi
    case "$arg" in
        --input|--template|--output|--journal) expect_path=1 ;;
    esac
    args+=("$arg")
done

docker run --rm --network none --read-only --tmpfs /tmp \
    --cap-drop ALL --security-opt no-new-privileges \
    --user "$(id -u):$(id -g)" \
    -v "$root:/work" "$IMAGE" "${args[@]}"
code=$?

case "$code" in
    0|1|2) exit "$code" ;;
    *) echo "ack-doc : échec de l'exécution Docker (code $code)." >&2; exit 2 ;;
esac
