from ack_doc import errors
from ack_doc.tag_parser import parse_tags


def codes(pages):
    return [a.code for a in parse_tags(pages).anomalies]


def test_well_formed():
    r = parse_tags(["[[ANACK]]ACK0001[[/ANACK]] [[ORNUM]]1[[/ORNUM]]"])
    assert not r.anomalies
    assert [o.name for o in r.occurrences] == ["ANACK", "ORNUM"]
    assert r.occurrences[0].raw_value == "ACK0001"


def test_space_tolerance_and_case():
    r = parse_tags(["[[ A N A C K ]]x[[ / ANACK ]]"])
    assert not r.anomalies


def test_lowercase_name_is_malformed():
    assert errors.MALFORMED_TAG in codes(["[[anack]]x[[/anack]]"])


def test_single_and_triple_brackets():
    assert errors.MALFORMED_TAG in codes(["[ANACK]x[/ANACK]"])
    assert errors.MALFORMED_TAG in codes(["[[[ANACK]]]x[[[/ANACK]]]"])


def test_unclosed():
    assert errors.UNCLOSED_TAG in codes(["[[EXSUM]]abc"])


def test_unmatched_closing():
    assert errors.UNMATCHED_CLOSING_TAG in codes(["abc[[/EXSUM]]"])


def test_nested():
    assert errors.NESTED_TAG in codes(["[[EXSUM]]a [[ORNUM]]1[[/ORNUM]] b[[/EXSUM]]"])


def test_exsum_across_pages():
    r = parse_tags(["[[EXSUM]]début", "fin[[/EXSUM]]"])
    assert errors.EXSUM_CROSSES_PAGE in [a.code for a in r.anomalies]
    assert r.occurrences[0].raw_value is None


def test_marker_split_between_pages():
    assert errors.MALFORMED_TAG in codes(["texte [[ANA", "CK]]ACK0001[[/ANACK]]"])
    assert errors.MALFORMED_TAG in codes(["texte [[ANACK]", "]ACK0001[[/ANACK]]"])


def test_template_unknown_tag():
    r = parse_tags(["[[FOO]]x[[/FOO]]"], allow_unknown=True)
    assert any(a.code == "UNKNOWN_TAG" for a in r.anomalies)
    assert not parse_tags(["[[FOO]]x[[/FOO]]"]).anomalies
