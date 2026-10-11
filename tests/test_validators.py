import pytest

from ack_doc.validators import validate_anack, validate_exsum, validate_ornum


@pytest.mark.parametrize("raw,ok", [
    ("ACK0001", True), (" \nACK0001\t", True), ("ack0001", False), ("ACK001", False),
    ("ACK00012", False), ("ACK000１", False), ("", False),
])
def test_anack(raw, ok):
    assert (validate_anack(raw)[0] is not None) is ok


@pytest.mark.parametrize("raw,ok", [
    ("0", True), ("9", True), ("10", False), ("", False), ("a", False), ("１", False),
])
def test_ornum(raw, ok):
    assert (validate_ornum(raw)[0] is not None) is ok


@pytest.mark.parametrize("raw,ok", [
    ("Un résumé", True), ("", False), ("   ", False), ("ACK0001 suite", False),
    ("1 premier", False), ("\u00a0texte", False), ("texte\u00a0", False),
    ("a\x00b", False), ("ligne1\nligne2", True), ("<b>x</b> & y", True),
])
def test_exsum(raw, ok):
    assert (validate_exsum(raw)[0] is not None) is ok


def test_exsum_strips_ascii_only():
    assert validate_exsum("  \n texte \t")[0] == "texte"
