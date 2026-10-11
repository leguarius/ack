"""Tests d'intégration du CLI (le rendu WeasyPrint est simulé si indisponible)."""

import pytest

from ack_doc import cli, renderer
from tests.helpers import good_pdf, load_journal, make_pdf, make_template

try:
    import weasyprint  # noqa: F401

    HAS_WEASY = True
except (OSError, ImportError):
    HAS_WEASY = False


@pytest.fixture(autouse=True)
def fake_render(monkeypatch):
    if not HAS_WEASY:
        monkeypatch.setattr(
            renderer, "render_pdf", lambda md, target: target.write_bytes(b"%PDF-1.7 fake")
        )


@pytest.fixture
def env(tmp_path):
    (tmp_path / "in").mkdir()
    (tmp_path / "out").mkdir()
    tpl = make_template(tmp_path / "t.md", "# Titre\n\n[[ANACK]]ACK0001[[/ANACK]]\n")
    return tmp_path, tpl


def run(tmp_path, tpl):
    return cli.main([
        "--input", str(tmp_path / "in"), "--template", str(tpl),
        "--output", str(tmp_path / "out" / "r.pdf"), "--journal", str(tmp_path / "out" / "j.json"),
    ])


def test_success(env):
    tmp, tpl = env
    good_pdf(tmp / "in" / "sub" / "a.pdf", exsum="Premier\nSecond")
    assert run(tmp, tpl) == 0
    md = (tmp / "out" / "r.md").read_text(encoding="utf-8")
    assert "Premier\nSecond" in md and "(../in/sub/a.pdf)" in md
    assert (tmp / "out" / "r.pdf").read_bytes().startswith(b"%PDF-")
    j = load_journal(tmp / "out" / "j.json")
    assert j["status"] == "success" and j["valid_count"] == 1
    assert j["files"][0]["path"] == "sub/a.pdf"


def test_validation_failure_no_output(env):
    tmp, tpl = env
    good_pdf(tmp / "in" / "a.pdf")
    good_pdf(tmp / "in" / "b.pdf")  # couple dupliqué
    make_pdf(tmp / "in" / "c.pdf", ["rien"])
    assert run(tmp, tpl) == 1
    assert not (tmp / "out" / "r.md").exists() and not (tmp / "out" / "r.pdf").exists()
    j = load_journal(tmp / "out" / "j.json")
    assert j["status"] == "validation_failed" and j["invalid_count"] == 3
    codes = {e["code"] for f in j["files"] for e in f["errors"]}
    assert {"DUPLICATE_ANACK_ORNUM", "MISSING_TAG"} <= codes


def test_unreadable_pdf(env):
    tmp, tpl = env
    (tmp / "in" / "bad.pdf").write_bytes(b"not a pdf")
    assert run(tmp, tpl) == 1
    j = load_journal(tmp / "out" / "j.json")
    assert j["files"][0]["errors"][0]["code"] == "PDF_UNREADABLE"


def test_no_pdf(env):
    tmp, tpl = env
    assert run(tmp, tpl) == 1
    assert load_journal(tmp / "out" / "j.json")["errors"][0]["code"] == "NO_PDF_FOUND"


def test_anack_not_in_template(env):
    tmp, tpl = env
    good_pdf(tmp / "in" / "a.pdf", anack="ACK0009")
    assert run(tmp, tpl) == 1


def test_output_exists_not_overwritten(env):
    tmp, tpl = env
    good_pdf(tmp / "in" / "a.pdf")
    (tmp / "out" / "r.pdf").write_bytes(b"old")
    assert run(tmp, tpl) == 2
    assert (tmp / "out" / "r.pdf").read_bytes() == b"old"
    assert not (tmp / "out" / "r.md").exists()
    assert load_journal(tmp / "out" / "j.json")["status"] == "execution_failed"


def test_missing_output_dir_and_input_dir(env):
    tmp, tpl = env
    assert cli.main(["--input", str(tmp / "nope"), "--template", str(tpl),
                     "--output", str(tmp / "out" / "r.pdf"), "--journal", str(tmp / "out" / "j.json")]) == 2
    assert cli.main(["--input", str(tmp / "in"), "--template", str(tpl),
                     "--output", str(tmp / "zz" / "r.pdf"), "--journal", str(tmp / "out" / "j.json")]) == 2


def test_invalid_template(env):
    tmp, _ = env
    good_pdf(tmp / "in" / "a.pdf")
    bad = make_template(tmp / "bad.md", "[[ORNUM]]1[[/ORNUM]]")
    assert run(tmp, bad) == 1


def test_template_not_utf8(env):
    tmp, _ = env
    bad = tmp / "latin.md"
    bad.write_bytes("é [[ANACK]]ACK0001[[/ANACK]]".encode("latin-1"))
    assert run(tmp, bad) == 2


def test_missing_args():
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2


def test_journal_replaced(env):
    tmp, tpl = env
    (tmp / "out" / "j.json").write_text("old")
    run(tmp, tpl)
    assert load_journal(tmp / "out" / "j.json")["schema_version"] == "1.0"


@pytest.mark.skipif(not HAS_WEASY, reason="WeasyPrint/Pango indisponible")
def test_real_render_fonts(env):
    import pymupdf

    tmp, tpl = env
    good_pdf(tmp / "in" / "a.pdf", exsum="Éléments <b>gras</b> & co")
    assert run(tmp, tpl) == 0
    doc = pymupdf.open(tmp / "out" / "r.pdf")
    fonts = {f[3] for page in doc for f in page.get_fonts()}
    assert fonts and all("NotoSans" in f for f in fonts), fonts
    assert "<b>gras</b>" in doc[0].get_text()
