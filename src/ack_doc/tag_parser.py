"""Analyseur déterministe des balises ``[[NOM]]contenu[[/NOM]]`` (TEC-019 à TEC-025, TEC-077 à TEC-079).

Les pages sont concaténées avec un séparateur explicite de frontière de page
(``PAGE_SEPARATOR``) qui n'appartient à aucune classe d'espacement tolérée : il ne peut
donc être ni ignoré à l'intérieur d'un marqueur, ni supprimé par la normalisation.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass, field

from ack_doc import errors

KNOWN_TAGS = ("ANACK", "ORNUM", "EXSUM")
PAGE_SEPARATOR = "\x0c"
ASCII_WHITESPACE = " \t\n\r"

UNKNOWN_TAG = "UNKNOWN_TAG"  # code interne, uniquement utilisé pour le template

_WS = r"[ \t\r\n]*"


def _fuzzy(word: str) -> str:
    """Motif insensible à la casse tolérant des espaces ASCII entre les caractères."""
    return _WS.join(f"[{c}{c.lower()}]" for c in word)


_OPEN = rf"\[(?:{_WS}\[)*"
_CLOSE = rf"\](?:{_WS}\])*"


def _token_pattern(allow_unknown: bool) -> re.Pattern[str]:
    names = "|".join(_fuzzy(n) for n in KNOWN_TAGS)
    if allow_unknown:
        names += r"|[A-Za-z_][A-Za-z0-9_]*"
    return re.compile(
        rf"(?P<open>{_OPEN}){_WS}(?P<slash>/?){_WS}(?P<name>{names}){_WS}(?P<close>{_CLOSE})"
    )


_PDF_PATTERN = _token_pattern(False)
_TEMPLATE_PATTERN = _token_pattern(True)

_PREFIXES = "|".join(_fuzzy(n[:k]) for n in KNOWN_TAGS for k in range(1, len(n) + 1))
_SUFFIXES = "|".join(_fuzzy(n[-k:]) for n in KNOWN_TAGS for k in range(1, len(n) + 1))
# Fragment d'un marqueur interrompu par une fin de page, ou repris en début de page.
_END_FRAGMENT = re.compile(rf"\[{_WS}\[{_WS}/?{_WS}(?:{_PREFIXES})?{_WS}\]?{_WS}\Z")
_START_FRAGMENT = re.compile(rf"\A{_WS}(?:(?:{_SUFFIXES}){_WS}\]{{1,2}}|\]\])")


@dataclass(frozen=True)
class TagOccurrence:
    """Balise complète (ouverture, contenu, fermeture)."""

    name: str
    raw_value: str | None  # None lorsque la balise s'étend sur plusieurs pages
    start: int
    end: int
    page: int
    end_page: int


@dataclass(frozen=True)
class TagAnomaly:
    code: str
    tag: str | None
    page: int | None
    message: str


@dataclass
class ParseResult:
    occurrences: list[TagOccurrence] = field(default_factory=list)
    anomalies: list[TagAnomaly] = field(default_factory=list)


@dataclass(frozen=True)
class _Token:
    start: int
    end: int
    closing: bool
    name: str


def normalize_value(raw: str) -> str:
    """Retire uniquement les espaces ASCII périphériques (TEC-080)."""
    return raw.strip(ASCII_WHITESPACE)


def _snippet(text: str) -> str:
    compact = re.sub(r"[ \t\r\n]+", " ", text)
    return compact if len(compact) <= 40 else compact[:37] + "..."


def parse_tags(pages: Sequence[str], *, allow_unknown: bool = False) -> ParseResult:
    """Analyse les balises du texte de ``pages`` (une chaîne par page, numérotées dès 1)."""
    text = PAGE_SEPARATOR.join(pages)
    offsets: list[int] = []
    position = 0
    for page in pages:
        offsets.append(position)
        position += len(page) + 1

    def page_of(index: int) -> int:
        return max(bisect_right(offsets, index), 1)

    result = ParseResult()
    tokens: list[_Token] = []
    pattern = _TEMPLATE_PATTERN if allow_unknown else _PDF_PATTERN

    for match in pattern.finditer(text):
        name = re.sub(r"[ \t\r\n]+", "", match["name"])
        open_count = match["open"].count("[")
        close_count = match["close"].count("]")
        page = page_of(match.start())
        well_formed_brackets = open_count == 2 and close_count == 2

        if name in KNOWN_TAGS:
            if well_formed_brackets:
                tokens.append(_Token(match.start(), match.end(), bool(match["slash"]), name))
            else:
                result.anomalies.append(
                    TagAnomaly(
                        errors.MALFORMED_TAG,
                        name,
                        page,
                        f"Balise {name} mal formée : « {_snippet(match.group(0))} »",
                    )
                )
        elif name.upper() in KNOWN_TAGS:
            tag = name.upper()
            result.anomalies.append(
                TagAnomaly(
                    errors.MALFORMED_TAG,
                    tag,
                    page,
                    f"Nom de balise à la casse incorrecte : « {_snippet(match.group(0))} » "
                    f"(attendu : {tag})",
                )
            )
        elif allow_unknown and well_formed_brackets:
            result.anomalies.append(
                TagAnomaly(
                    UNKNOWN_TAG,
                    name,
                    page,
                    f"Balise inconnue : « {_snippet(match.group(0))} »",
                )
            )

    stack: list[_Token] = []
    for token in tokens:
        page = page_of(token.start)
        if not token.closing:
            if stack:
                result.anomalies.append(
                    TagAnomaly(
                        errors.NESTED_TAG,
                        token.name,
                        page,
                        f"Balise {token.name} imbriquée dans la balise {stack[-1].name}",
                    )
                )
            stack.append(token)
            continue

        index = next(
            (i for i in range(len(stack) - 1, -1, -1) if stack[i].name == token.name), None
        )
        if index is None:
            result.anomalies.append(
                TagAnomaly(
                    errors.UNMATCHED_CLOSING_TAG,
                    token.name,
                    page,
                    f"Balise de fermeture {token.name} sans balise d'ouverture",
                )
            )
            continue
        while len(stack) - 1 > index:
            unclosed = stack.pop()
            result.anomalies.append(
                TagAnomaly(
                    errors.UNCLOSED_TAG,
                    unclosed.name,
                    page_of(unclosed.start),
                    f"Balise {unclosed.name} ouverte et non fermée",
                )
            )
        opening = stack.pop()
        open_page = page_of(opening.start)
        if open_page != page:
            raw_value = None
            if token.name == "EXSUM":
                result.anomalies.append(
                    TagAnomaly(
                        errors.EXSUM_CROSSES_PAGE,
                        token.name,
                        open_page,
                        f"Le résumé EXSUM s'étend de la page {open_page} à la page {page}",
                    )
                )
            else:
                result.anomalies.append(
                    TagAnomaly(
                        errors.MALFORMED_TAG,
                        token.name,
                        open_page,
                        f"La balise {token.name} s'étend de la page {open_page} à la page {page}",
                    )
                )
        else:
            raw_value = text[opening.end : token.start]
        result.occurrences.append(
            TagOccurrence(token.name, raw_value, opening.start, token.end, open_page, page)
        )

    for unclosed in stack:
        result.anomalies.append(
            TagAnomaly(
                errors.UNCLOSED_TAG,
                unclosed.name,
                page_of(unclosed.start),
                f"Balise {unclosed.name} ouverte et non fermée",
            )
        )

    # Marqueurs coupés par une frontière de page (TEC-079) : un signalement par frontière.
    for index in range(len(pages) - 1):
        if _END_FRAGMENT.search(pages[index]):
            reported_page = index + 1
        elif _START_FRAGMENT.search(pages[index + 1]):
            reported_page = index + 2
        else:
            continue
        result.anomalies.append(
            TagAnomaly(
                errors.MALFORMED_TAG,
                None,
                reported_page,
                f"Marqueur réparti sur deux pages (frontière entre les pages {index + 1} "
                f"et {index + 2})",
            )
        )

    result.anomalies.sort(key=lambda a: a.page or 0)
    return result
