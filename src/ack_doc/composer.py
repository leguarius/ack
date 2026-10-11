"""Composition du Markdown final (TEC-036 à TEC-048, TEC-084 à TEC-096)."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import quote

from ack_doc.models import SourceDocument
from ack_doc.template import TemplateInfo

LINK_LABEL = "Document source"

_ALWAYS_ESCAPE = set("\\`*_[]<>&~|")
_LINE_START_ESCAPE = set("#+-=")
_ORDERED_RE = re.compile(r"^(\d{1,9})([.)])")


def escape_markdown_line(line: str) -> str:
    """Neutralise Markdown et HTML dans une ligne de résumé."""
    stripped = line.strip(" \t")
    if not stripped:
        return ""
    lead = line[: len(line) - len(line.lstrip(" \t"))]
    prefix = "&nbsp;" * sum(4 if c == "\t" else 1 for c in lead)
    body = line.lstrip(" \t").rstrip(" \t")

    out: list[str] = []
    for char in body:
        out.append("\\" + char if char in _ALWAYS_ESCAPE else char)
    escaped = "".join(out)

    if not prefix:
        if escaped[0] in _LINE_START_ESCAPE:
            escaped = "\\" + escaped
        else:
            match = _ORDERED_RE.match(escaped)
            if match:
                end = match.end(1)
                escaped = escaped[:end] + "\\" + escaped[end:]
    return prefix + escaped


def escape_summary(text: str) -> str:
    lines = re.split(r"\r\n|\r|\n", text)
    return "\n".join(escape_markdown_line(line) for line in lines)


def relative_link(source: Path, markdown_path: Path) -> str:
    """Chemin relatif au dossier du fichier Markdown final, en POSIX, encodé en pourcentage."""
    relative = os.path.relpath(source, markdown_path.parent)
    return quote(relative.replace(os.sep, "/"), safe="/")


def render_entry(document: SourceDocument, markdown_path: Path) -> str:
    return (
        "<!-- ack:entry:start -->\n"
        "<!-- ack:summary:start -->\n"
        f"{escape_summary(document.exsum)}\n"
        "<!-- ack:summary:end -->\n"
        "\n"
        "<!-- ack:link:start -->\n"
        f"[{LINK_LABEL}]({relative_link(document.path, markdown_path)})\n"
        "<!-- ack:link:end -->\n"
        "<!-- ack:entry:end -->"
    )


def compose_markdown(
    template: TemplateInfo, documents: Sequence[SourceDocument], markdown_path: Path
) -> str:
    """Remplace chaque marqueur ANACK du template par les entrées triées par ORNUM."""
    by_key: dict[str, list[SourceDocument]] = defaultdict(list)
    for document in documents:
        by_key[document.anack].append(document)

    text = template.text
    result: list[str] = []
    cursor = 0
    for placeholder in sorted(template.placeholders, key=lambda p: p.start):
        entries = sorted(by_key.get(placeholder.key, []), key=lambda d: d.ornum)
        block = "\n\n".join(render_entry(d, markdown_path) for d in entries)

        start, end = placeholder.start, placeholder.end
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        line_end = len(text) if line_end == -1 else line_end
        alone = not text[line_start:start].strip(" \t") and not text[end:line_end].strip(" \t")

        if alone:
            result.append(text[cursor:line_start])
            if block:
                result.append(block)
                cursor = line_end
            else:
                cursor = min(line_end + 1, len(text))
        else:
            result.append(text[cursor:start])
            if block:
                before = "" if start == 0 or text[start - 1] == "\n" else "\n\n"
                after = "" if end >= len(text) or text[end] == "\n" else "\n\n"
                result.append(f"{before}{block}{after}")
            cursor = end
    result.append(text[cursor:])
    output = "".join(result)
    return output if output.endswith("\n") else output + "\n"
