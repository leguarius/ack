from pathlib import Path

from ack_doc.composer import compose_markdown, escape_summary, relative_link
from ack_doc.models import SourceDocument
from ack_doc.template import validate_template


def doc(root, name, anack, ornum, exsum):
    return SourceDocument(root / name, Path(name), anack, ornum, exsum)


def test_escape_markdown_and_html():
    out = escape_summary("<script>x</script> *a* _b_ [l](u) & `c`")
    assert "<" not in out.replace("\\<", "")
    assert "\\*a\\*" in out and "\\[l\\]" in out and "\\&" in out


def test_escape_line_start():
    assert escape_summary("# titre").startswith("\\#")
    assert escape_summary("1. item").startswith("1\\.")
    assert escape_summary("- item").startswith("\\-")


def test_line_breaks_preserved():
    assert escape_summary("a\r\nb\rc\nd") == "a\nb\nc\nd"


def test_relative_link(tmp_path):
    md = tmp_path / "out" / "r.md"
    assert relative_link(tmp_path / "in" / "d é.pdf", md) == "../in/d%20%C3%A9.pdf"


def test_compose_sorted_by_ornum(tmp_path):
    tpl = validate_template("# T\n\n[[ANACK]]ACK0001[[/ANACK]]\n\nFin\n")
    out = compose_markdown(
        tpl,
        [doc(tmp_path, "b.pdf", "ACK0001", 2, "second"), doc(tmp_path, "a.pdf", "ACK0001", 1, "premier")],
        tmp_path / "r.md",
    )
    assert out.index("premier") < out.index("second")
    assert "[[ANACK]]" not in out and out.endswith("Fin\n")


def test_compose_empty_key_removed(tmp_path):
    tpl = validate_template("A\n[[ANACK]]ACK0002[[/ANACK]]\nB\n")
    assert compose_markdown(tpl, [], tmp_path / "r.md") == "A\nB\n"


def test_template_rules():
    assert validate_template("").issues
    assert validate_template("[[ANACK]]ACK0001[[/ANACK]]").is_valid
    assert validate_template("[[ORNUM]]1[[/ORNUM]]").issues
    assert validate_template("[[ANACK]]X[[/ANACK]]").issues
    dup = validate_template("[[ANACK]]ACK0001[[/ANACK]] [[ANACK]]ACK0001[[/ANACK]]")
    assert any(i.code == "DUPLICATE_TEMPLATE_ANACK" for i in dup.issues)
    assert validate_template("[[ANACK]]ACK0001").issues


def test_intro_markers_in_template_and_html():
    from ack_doc.renderer import markdown_to_html

    text = (
        "## S\n\n<!-- ack:intro:start -->\nIntro *x*\n<!-- ack:intro:end -->\n\n"
        "[[ANACK]]ACK0001[[/ANACK]]\n"
    )
    assert validate_template(text).is_valid
    html = markdown_to_html(text)
    assert '<section class="ack-intro"><div class="ack-intro-text">' in html
    assert "<em>x</em>" in html and "</div></section>" in html


def test_intro_markers_unbalanced_rejected():
    for text in (
        "<!-- ack:intro:start -->\nx\n[[ANACK]]ACK0001[[/ANACK]]\n",
        "<!-- ack:intro:start -->\n<!-- ack:intro:start -->\n<!-- ack:intro:end -->\n",
        "<!-- ack:intro:end -->\n[[ANACK]]ACK0001[[/ANACK]]\n",
    ):
        assert not validate_template(text).is_valid
