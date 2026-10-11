"""Utilitaires de tests : génération de PDF."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf


def make_pdf(path: Path, pages: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        y = 72
        for line in text.split("\n"):
            if line:
                page.insert_text((50, y), line, fontsize=10)
            y += 14
    doc.save(path)
    doc.close()
    return path


def good_pdf(path: Path, anack="ACK0001", ornum="1", exsum="Résumé du document") -> Path:
    return make_pdf(
        path, [f"[[ANACK]]{anack}[[/ANACK]]\n[[ORNUM]]{ornum}[[/ORNUM]]\n[[EXSUM]]{exsum}[[/EXSUM]]"]
    )


def make_template(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def load_journal(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
