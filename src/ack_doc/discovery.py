"""Découverte récursive des PDF (TEC-005 à TEC-011)."""

from __future__ import annotations

import os
from pathlib import Path

from ack_doc import errors


def _raise(exc: OSError) -> None:
    raise errors.TechnicalError(
        errors.INPUT_DIR_ERROR,
        f"Parcours impossible : {exc.strerror or exc}",
        str(exc.filename) if exc.filename else None,
    ) from exc


def discover_pdfs(root: Path) -> list[Path]:
    """Liste triée des fichiers ``.pdf`` (insensible à la casse) sous ``root``."""
    found: list[Path] = []
    for directory, dirnames, filenames in os.walk(root, onerror=_raise):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(directory, name)
            if name.lower().endswith(".pdf") and full.is_file():
                found.append(full)
    return found
