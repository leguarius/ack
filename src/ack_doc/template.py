"""Lecture et validation du template Markdown (TEC-029 à TEC-035, TEC-081 à TEC-083)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ack_doc import errors
from ack_doc.models import ValidationIssue
from ack_doc.tag_parser import UNKNOWN_TAG, normalize_value, parse_tags

_KEY_RE = re.compile(r"ACK[0-9]{4}")
_INTRO_RE = re.compile(r"^<!-- ack:intro:(start|end) -->[ \t]*$")


@dataclass(frozen=True)
class Placeholder:
    """Emplacement ``[[ANACK]]clé[[/ANACK]]`` : intervalle [start, end) dans le texte."""

    key: str
    start: int
    end: int


@dataclass
class TemplateInfo:
    text: str
    placeholders: list[Placeholder] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def keys(self) -> set[str]:
        return {p.key for p in self.placeholders}


def read_template(path: Path) -> str:
    """Lit le template (UTF-8 strict). Lève ``TechnicalError`` (code 2) en cas d'échec."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise errors.TechnicalError(
            errors.TEMPLATE_READ_ERROR,
            f"Impossible de lire le template : {exc.strerror or exc}",
            str(path),
        ) from exc
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise errors.TechnicalError(
            errors.TEMPLATE_ENCODING_ERROR,
            f"Le template n'est pas encodé en UTF-8 valide : {exc}",
            str(path),
        ) from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


def validate_template(text: str, file_label: str | None = None) -> TemplateInfo:
    """Valide un texte de template déjà décodé et dont les fins de ligne sont normalisées."""
    info = TemplateInfo(text=text)

    def issue(message: str, code: str = errors.INVALID_TEMPLATE, tag: str | None = "ANACK") -> None:
        info.issues.append(ValidationIssue(code, message, file_label, None, tag))

    if not text.strip(" \t\n\r"):
        issue("Le modèle est vide", tag=None)
        return info

    depth = 0
    for line in text.split("\n"):
        marker = _INTRO_RE.match(line)
        if not marker:
            continue
        depth += 1 if marker.group(1) == "start" else -1
        if depth not in (0, 1):
            issue("Marqueurs de propos introductif imbriqués ou non appariés", tag="ack:intro")
            depth = 0
    if depth:
        issue("Propos introductif non fermé dans le modèle", tag="ack:intro")

    parsed = parse_tags([text], allow_unknown=True)
    for anomaly in parsed.anomalies:
        if anomaly.code == UNKNOWN_TAG:
            issue(anomaly.message, tag=anomaly.tag)
        else:
            issue(f"{anomaly.code} : {anomaly.message}", tag=anomaly.tag)

    seen: dict[str, int] = {}
    for occurrence in sorted(parsed.occurrences, key=lambda o: o.start):
        if occurrence.name != "ANACK":
            issue(
                f"Balise {occurrence.name} non autorisée dans le modèle (seules les balises "
                "ANACK sont admises)",
                tag=occurrence.name,
            )
            continue
        key = normalize_value(occurrence.raw_value or "")
        if not _KEY_RE.fullmatch(key):
            issue("Clé ANACK du modèle invalide : « ACK » suivi de quatre chiffres ASCII attendu")
            continue
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            issue(
                f"La clé {key} apparaît plusieurs fois dans le modèle",
                code=errors.DUPLICATE_TEMPLATE_ANACK,
            )
        info.placeholders.append(Placeholder(key, occurrence.start, occurrence.end))
    return info


def load_template(path: Path) -> TemplateInfo:
    text = read_template(path)
    return validate_template(text, str(path))
