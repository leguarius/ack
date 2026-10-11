"""Validation des contenus des balises et des règles métier (TEC-020 à TEC-025, TEC-030, TEC-035)."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

from ack_doc import errors
from ack_doc.models import DocumentAnalysis, PageText, ValidationIssue
from ack_doc.tag_parser import KNOWN_TAGS, TagOccurrence, normalize_value, parse_tags

_ANACK_RE = re.compile(r"ACK[0-9]{4}")
_ORNUM_RE = re.compile(r"[0-9]")
_ASCII_DIGITS = "0123456789"
_ALLOWED_CONTROLS = "\t\n\r"


def validate_anack(raw: str) -> tuple[str | None, str | None]:
    """Retourne (valeur normalisée, message d'erreur)."""
    value = normalize_value(raw)
    if _ANACK_RE.fullmatch(value):
        return value, None
    return None, "Format ANACK invalide : « ACK » suivi de quatre chiffres ASCII attendu"


def validate_ornum(raw: str) -> tuple[int | None, str | None]:
    value = normalize_value(raw)
    if _ORNUM_RE.fullmatch(value):
        return int(value), None
    return None, "Format ORNUM invalide : un chiffre ASCII unique (0 à 9) est attendu"


def validate_exsum(raw: str) -> tuple[str | None, str | None]:
    value = normalize_value(raw)
    if not value:
        return None, "Résumé EXSUM vide"
    if value.startswith("ACK"):
        return None, "Le résumé EXSUM ne doit pas commencer par « ACK »"
    if value[0] in _ASCII_DIGITS:
        return None, "Le résumé EXSUM ne doit pas commencer par un chiffre"
    if value[0].isspace() or value[-1].isspace():
        return None, "Le résumé EXSUM comporte un espace Unicode périphérique non autorisé"
    for char in value:
        if unicodedata.category(char) == "Cc" and char not in _ALLOWED_CONTROLS:
            return None, f"Le résumé EXSUM contient un caractère de contrôle (U+{ord(char):04X})"
    return value, None


def _is_blank(text: str) -> bool:
    return not text.strip()


def analyze_pdf(path: Path, relative_path: str, pages: Sequence[PageText]) -> DocumentAnalysis:
    """Valide la structure et les contenus des balises d'un PDF déjà extrait."""
    analysis = DocumentAnalysis(path=path, relative_path=relative_path)
    issues = analysis.issues

    def issue(code: str, message: str, page: int | None = None, tag: str | None = None) -> None:
        issues.append(ValidationIssue(code, message, relative_path, page, tag))

    if all(_is_blank(page.text) for page in pages):
        issue(errors.PDF_NO_TEXT, "Le PDF ne contient aucun texte exploitable (aucun OCR n'est effectué)")
        return analysis

    parsed = parse_tags([page.text for page in pages])
    for anomaly in parsed.anomalies:
        issue(anomaly.code, anomaly.message, anomaly.page, anomaly.tag)

    by_name: dict[str, list[TagOccurrence]] = defaultdict(list)
    for occurrence in parsed.occurrences:
        by_name[occurrence.name].append(occurrence)

    values: dict[str, object] = {}
    validators = {
        "ANACK": (validate_anack, errors.INVALID_ANACK),
        "ORNUM": (validate_ornum, errors.INVALID_ORNUM),
        "EXSUM": (validate_exsum, errors.INVALID_EXSUM),
    }
    for name in KNOWN_TAGS:
        occurrences = by_name[name]
        if not occurrences:
            issue(errors.MISSING_TAG, f"Balise {name} obligatoire absente", None, name)
            continue
        if len(occurrences) > 1:
            pages_list = ", ".join(str(o.page) for o in occurrences)
            issue(
                errors.DUPLICATE_TAG,
                f"Balise {name} présente {len(occurrences)} fois (pages {pages_list})",
                occurrences[1].page,
                name,
            )
        validate, code = validators[name]
        valid_values = []
        for occurrence in occurrences:
            if occurrence.raw_value is None:
                continue  # déjà signalé par l'analyseur (balise répartie sur plusieurs pages)
            value, message = validate(occurrence.raw_value)
            if message is not None:
                issue(code, message, occurrence.page, name)
            else:
                valid_values.append(value)
        if len(occurrences) == 1 and len(valid_values) == 1:
            values[name] = valid_values[0]

    analysis.anack = values.get("ANACK")  # type: ignore[assignment]
    analysis.ornum = values.get("ORNUM")  # type: ignore[assignment]
    analysis.exsum = values.get("EXSUM")  # type: ignore[assignment]
    return analysis


def cross_validate(analyses: Iterable[DocumentAnalysis], template_keys: set[str]) -> None:
    """Validation croisée : clés absentes du template et couples ANACK + ORNUM dupliqués."""
    analyses = list(analyses)

    for analysis in analyses:
        if analysis.anack is not None and analysis.anack not in template_keys:
            analysis.issues.append(
                ValidationIssue(
                    errors.ANACK_NOT_IN_TEMPLATE,
                    f"La clé {analysis.anack} n'est pas prévue dans le modèle",
                    analysis.relative_path,
                    None,
                    "ANACK",
                )
            )

    groups: dict[tuple[str, int], list[DocumentAnalysis]] = defaultdict(list)
    for analysis in analyses:
        if analysis.anack is not None and analysis.ornum is not None:
            groups[(analysis.anack, analysis.ornum)].append(analysis)
    for (anack, ornum), members in groups.items():
        if len(members) < 2:
            continue
        for analysis in members:
            others = ", ".join(m.relative_path for m in members if m is not analysis)
            analysis.issues.append(
                ValidationIssue(
                    errors.DUPLICATE_ANACK_ORNUM,
                    f"Le couple ANACK {anack} / ORNUM {ornum} est déjà utilisé par : {others}",
                    analysis.relative_path,
                    None,
                    "ORNUM",
                )
            )
