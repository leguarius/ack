"""Interface en ligne de commande et orchestration (TEC-002 à TEC-004, TEC-049 à TEC-062)."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from ack_doc import __version__, errors
from ack_doc.composer import compose_markdown
from ack_doc.discovery import discover_pdfs
from ack_doc.journal import JournalData, write_journal
from ack_doc.models import DocumentAnalysis, ValidationIssue
from ack_doc.pdf_reader import PdfUnreadable, read_pdf_pages
from ack_doc.template import load_template
from ack_doc.validators import analyze_pdf, cross_validate


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # code retour 2 pour tout défaut d'utilisation
        self.print_usage(sys.stderr)
        self.exit(errors.EXIT_TECHNICAL, f"ack-doc : erreur : {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="ack-doc",
        description="Valide des PDF balisés et génère un récapitulatif Markdown et PDF.",
    )
    parser.add_argument("--input", required=True, help="répertoire des PDF sources")
    parser.add_argument("--template", required=True, help="modèle Markdown")
    parser.add_argument("--output", required=True, help="PDF final (le Markdown porte le même nom en .md)")
    parser.add_argument("--journal", required=True, help="journal JSON")
    parser.add_argument("--version", action="version", version=f"ack-doc {__version__}")
    return parser


def _abs(value: str) -> Path:
    return Path(os.path.abspath(value))


def _same(a: Path, b: Path) -> bool:
    return os.path.normcase(a) == os.path.normcase(b)


def _check_dir(path: Path, code: str, label: str) -> None:
    if not path.is_dir() or not os.access(path, os.R_OK | os.X_OK):
        raise errors.TechnicalError(code, f"{label} inexistant ou inaccessible", str(path))


def _publish(tmp: Path, final: Path) -> None:
    """Publie sans jamais écraser : lien physique, ou création exclusive à défaut."""
    try:
        os.link(tmp, final)
        os.unlink(tmp)
        return
    except FileExistsError as exc:
        raise errors.TechnicalError(
            errors.OUTPUT_EXISTS, "Le fichier de sortie est apparu pendant le traitement", str(final)
        ) from exc
    except (OSError, NotImplementedError):
        pass
    try:
        with open(final, "xb") as target, open(tmp, "rb") as source:
            target.write(source.read())
        os.unlink(tmp)
    except FileExistsError as exc:
        raise errors.TechnicalError(
            errors.OUTPUT_EXISTS, "Le fichier de sortie est apparu pendant le traitement", str(final)
        ) from exc


def _generate(template, documents, md_path: Path, pdf_path: Path) -> None:
    from ack_doc.renderer import render_pdf

    markdown = compose_markdown(template, documents, md_path)
    out_dir = pdf_path.parent
    tmp_files: list[Path] = []
    published: list[Path] = []
    try:
        fd, name = tempfile.mkstemp(prefix=".ack-doc-", suffix=".md", dir=out_dir)
        tmp_md = Path(name)
        tmp_files.append(tmp_md)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown)

        fd, name = tempfile.mkstemp(prefix=".ack-doc-", suffix=".pdf", dir=out_dir)
        os.close(fd)
        tmp_pdf = Path(name)
        tmp_files.append(tmp_pdf)
        render_pdf(markdown, tmp_pdf)

        if tmp_md.stat().st_size == 0 or tmp_pdf.stat().st_size == 0:
            raise errors.TechnicalError(errors.RENDER_ERROR, "Fichier généré vide")
        with open(tmp_pdf, "rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise errors.TechnicalError(errors.RENDER_ERROR, "Le PDF généré est invalide")

        for tmp, final in ((tmp_md, md_path), (tmp_pdf, pdf_path)):
            _publish(tmp, final)
            published.append(final)
    except BaseException:
        for final in published:
            try:
                os.unlink(final)
            except OSError:
                pass
        raise
    finally:
        for tmp in tmp_files:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def run(args: argparse.Namespace) -> int:
    started = datetime.now().astimezone()
    clock = time.monotonic()
    input_dir = _abs(args.input)
    template_path = _abs(args.template)
    pdf_path = _abs(args.output)
    md_path = pdf_path.with_suffix(".md")
    journal_path = _abs(args.journal)

    data = JournalData(started_at=started)
    reached_control = False

    def global_issue(code: str, message: str, file: str | None = None) -> None:
        data.global_issues.append(ValidationIssue(code, message, file))

    try:
        try:
            _check_dir(journal_path.parent, errors.JOURNAL_DIR_ERROR, "Répertoire du journal")
        except errors.TechnicalError as exc:
            print(f"ack-doc : {exc.message} : {exc.file}", file=sys.stderr)
            return errors.EXIT_TECHNICAL

        try:
            _check_dir(input_dir, errors.INPUT_DIR_ERROR, "Répertoire d'entrée")
            _check_dir(pdf_path.parent, errors.OUTPUT_DIR_ERROR, "Répertoire de sortie")
            if _same(md_path, pdf_path):
                raise errors.TechnicalError(
                    errors.PATH_COLLISION,
                    "Le Markdown généré et le PDF final auraient le même chemin",
                    str(pdf_path),
                )
            protected = {"journal": journal_path, "template": template_path}
            for label, path in protected.items():
                for out_label, out in (("PDF", pdf_path), ("Markdown", md_path)):
                    if _same(path, out):
                        raise errors.TechnicalError(
                            errors.PATH_COLLISION,
                            f"Le fichier de sortie {out_label} entre en collision avec le {label}",
                            str(path),
                        )
            if _same(journal_path, template_path):
                raise errors.TechnicalError(
                    errors.PATH_COLLISION, "Le journal et le template ont le même chemin", str(journal_path)
                )

            template = load_template(template_path)
            if not template.is_valid:
                for issue in template.issues:
                    data.global_issues.append(
                        ValidationIssue(issue.code, issue.message, str(template_path), None, issue.tag)
                    )
                data.exit_code = errors.EXIT_VALIDATION
                return data.exit_code

            pdfs = discover_pdfs(input_dir)
            if not pdfs:
                global_issue(errors.NO_PDF_FOUND, "Aucun PDF trouvé dans le répertoire d'entrée")
                data.exit_code = errors.EXIT_VALIDATION
                return data.exit_code

            for path in pdfs:
                for out in (pdf_path, md_path, journal_path):
                    if _same(path, out):
                        raise errors.TechnicalError(
                            errors.PATH_COLLISION,
                            "Un fichier de sortie coïncide avec un PDF source",
                            str(path),
                        )

            reached_control = True
            for path in pdfs:
                relative = path.relative_to(input_dir).as_posix()
                try:
                    pages = read_pdf_pages(path)
                except PdfUnreadable as exc:
                    analysis = DocumentAnalysis(path, relative)
                    analysis.issues.append(
                        ValidationIssue(errors.PDF_UNREADABLE, str(exc), relative)
                    )
                else:
                    analysis = analyze_pdf(path, relative, pages)
                data.analyses.append(analysis)

            cross_validate(data.analyses, template.keys)

            if any(not a.is_valid for a in data.analyses):
                data.exit_code = errors.EXIT_VALIDATION
                return data.exit_code

            for out in (md_path, pdf_path):
                if os.path.lexists(out):
                    global_issue(errors.OUTPUT_EXISTS, "Le fichier de sortie existe déjà", str(out))
                    data.exit_code = errors.EXIT_TECHNICAL
                    return data.exit_code

            _generate(template, [a.to_source_document() for a in data.analyses], md_path, pdf_path)
            data.exit_code = errors.EXIT_SUCCESS
            return data.exit_code
        except errors.TechnicalError as exc:
            global_issue(exc.code, exc.message, exc.file)
            data.exit_code = errors.EXIT_TECHNICAL
            return data.exit_code
        except OSError as exc:
            global_issue(errors.IO_ERROR, f"Erreur d'accès aux fichiers : {exc}")
            data.exit_code = errors.EXIT_TECHNICAL
            return data.exit_code
        except Exception as exc:  # noqa: BLE001
            global_issue(errors.INTERNAL_ERROR, f"Erreur interne : {exc!r}")
            data.exit_code = errors.EXIT_TECHNICAL
            return data.exit_code
    finally:
        data.duration_seconds = time.monotonic() - clock
        try:
            write_journal(journal_path, data)
        except OSError as exc:
            print(f"ack-doc : écriture du journal impossible : {exc}", file=sys.stderr)
            data.exit_code = errors.EXIT_TECHNICAL
        if reached_control:
            print(f"{len(data.analyses)} PDF contrôlé(s) en {data.duration_seconds:.2f} s")
        _report(data)


def _report(data: JournalData) -> None:
    for analysis in data.analyses:
        for issue in analysis.issues:
            page = f" (page {issue.page})" if issue.page else ""
            print(f"{analysis.relative_path}{page} : {issue.code} : {issue.message}", file=sys.stderr)
    for issue in data.global_issues:
        where = f" [{issue.file}]" if issue.file else ""
        print(f"{issue.code} : {issue.message}{where}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code = run(args)
    return code


def entry() -> None:
    sys.exit(main())


if __name__ == "__main__":
    entry()
