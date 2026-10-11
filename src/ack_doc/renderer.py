"""Rendu Markdown -> HTML -> PDF (TEC-056 à TEC-075, TEC-097 à TEC-107)."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt

from ack_doc import errors

RESOURCES = Path(__file__).resolve().parent / "resources"
CSS_PATH = RESOURCES / "pdf.css"

_MARKER_RE = re.compile(r"^<!-- ack:(entry|summary|link|intro):(start|end) -->[ \t]*$")
_OPEN_HTML = {
    "entry": '<section class="ack-entry">\n',
    "summary": '<div class="ack-summary">',
    "link": '<div class="ack-link-bubble">',
    "intro": '<section class="ack-intro"><div class="ack-intro-text">',
}
_CLOSE_HTML = {
    "entry": "</section>\n",
    "summary": "</div>\n",
    "link": "</div>\n",
    "intro": "</div></section>\n",
}


def _ack_marker(state, start_line: int, end_line: int, silent: bool) -> bool:
    if state.is_code_block(start_line):
        return False
    begin = state.bMarks[start_line] + state.tShift[start_line]
    line = state.src[begin : state.eMarks[start_line]]
    match = _MARKER_RE.match(line)
    if not match:
        return False
    if silent:
        return True
    token = state.push("ack_marker", "", 0)
    token.meta = {"kind": match.group(1), "edge": match.group(2)}
    token.map = [start_line, start_line + 1]
    token.block = True
    state.line = start_line + 1
    return True


def _render_marker(self, tokens, idx, options, env) -> str:
    meta = tokens[idx].meta
    table = _OPEN_HTML if meta["edge"] == "start" else _CLOSE_HTML
    return table[meta["kind"]]


def make_markdown_parser() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "breaks": True, "linkify": False})
    md.enable(["table", "strikethrough"])
    md.block.ruler.before(
        "paragraph",
        "ack_marker",
        _ack_marker,
        {"alt": ["paragraph", "reference", "blockquote", "list"]},
    )
    md.add_render_rule("ack_marker", _render_marker)
    return md


def markdown_to_html(markdown: str) -> str:
    body = make_markdown_parser().render(markdown)
    return (
        '<!DOCTYPE html>\n<html lang="fr"><head><meta charset="utf-8">'
        '<title>ACK-DOC</title></head>\n<body>\n' + body + "</body></html>\n"
    )


def _prepare_fontconfig(workdir: Path) -> None:
    template = (RESOURCES / "fonts.conf").read_text(encoding="utf-8")
    cache = workdir / "fontcache"
    cache.mkdir(parents=True, exist_ok=True)
    config = workdir / "fonts.conf"
    config.write_text(
        template.replace("@FONTS_DIR@", (RESOURCES / "fonts").as_posix()).replace(
            "@CACHE_DIR@", cache.as_posix()
        ),
        encoding="utf-8",
    )
    os.environ["FONTCONFIG_FILE"] = str(config)


def render_pdf(markdown: str, target: Path) -> None:
    """Rend ``markdown`` en PDF dans ``target`` (fichier temporaire choisi par l'appelant)."""
    html_text = markdown_to_html(markdown)
    try:
        with tempfile.TemporaryDirectory(prefix="ack-doc-") as tmp:
            _prepare_fontconfig(Path(tmp))
            # Import tardif : fontconfig lit FONTCONFIG_FILE à la première initialisation.
            from weasyprint import CSS, HTML
            from weasyprint.text.fonts import FontConfiguration
            from weasyprint.urls import URLFetcher

            allowed = RESOURCES.resolve()

            class LocalResourceFetcher(URLFetcher):
                def fetch(self, url, headers=None):
                    if not url.startswith("file:"):
                        raise ValueError(f"Ressource externe refusée : {url}")
                    from urllib.parse import urlparse
                    from urllib.request import url2pathname

                    local = Path(url2pathname(urlparse(url).path)).resolve()
                    if allowed != local and allowed not in local.parents:
                        raise ValueError(f"Ressource locale refusée : {url}")
                    return super().fetch(url, headers)

            fetcher = LocalResourceFetcher()
            fonts = FontConfiguration()
            stylesheet = CSS(filename=str(CSS_PATH), font_config=fonts, url_fetcher=fetcher)
            HTML(string=html_text, url_fetcher=fetcher).write_pdf(
                str(target), stylesheets=[stylesheet], font_config=fonts
            )
    except errors.TechnicalError:
        raise
    except Exception as exc:  # noqa: BLE001 - toute défaillance du moteur est une erreur de rendu
        raise errors.TechnicalError(
            errors.RENDER_ERROR, f"Échec de la génération du PDF : {exc}"
        ) from exc
