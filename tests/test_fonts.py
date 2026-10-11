import hashlib
from pathlib import Path

FONTS = Path(__file__).resolve().parents[1] / "src" / "ack_doc" / "resources" / "fonts"


def test_font_checksums():
    for line in (FONTS / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ")
        assert hashlib.sha256((FONTS / name).read_bytes()).hexdigest() == digest, name
