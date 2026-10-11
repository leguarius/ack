"""Extraction du texte des PDF (TEC-012 à TEC-018). Aucun OCR."""

from __future__ import annotations

from pathlib import Path

from ack_doc import errors
from ack_doc.models import PageText


class PdfUnreadable(Exception):
    """PDF impossible à lire comme source exploitable (code PDF_UNREADABLE)."""


def read_pdf_pages(path: Path) -> list[PageText]:
    """Retourne le texte de chaque page.

    Lève ``TechnicalError`` si le fichier ne peut être lu (accès) et ``PdfUnreadable``
    si son contenu n'est pas exploitable (corrompu, chiffré, sans page).
    """
    import pymupdf

    try:
        data = path.read_bytes()
    except OSError as exc:
        raise errors.TechnicalError(
            errors.IO_ERROR, f"Lecture impossible : {exc.strerror or exc}", str(path)
        ) from exc

    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise PdfUnreadable(f"PDF corrompu ou illisible : {exc}") from exc

    try:
        if document.needs_pass:
            raise PdfUnreadable("PDF protégé par mot de passe")
        if document.page_count == 0:
            raise PdfUnreadable("PDF sans page")
        try:
            return [
                PageText(index + 1, page.get_text("text"))
                for index, page in enumerate(document)
            ]
        except (RuntimeError, ValueError) as exc:
            raise PdfUnreadable(f"Extraction du texte impossible : {exc}") from exc
    finally:
        document.close()
