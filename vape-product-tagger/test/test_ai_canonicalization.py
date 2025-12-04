from pathlib import Path

from main import ControlledTagger


def _make_tagger():
    return ControlledTagger(config_file=None, no_ai=True, verbose=False)


def test_normalize_map_contains_pen_style():
    ct = _make_tagger()
    norm = ct._normalize_tag('Pen Style')
    assert norm == 'pen_style'
    assert 'pen_style' in ct.normalized_map
    assert ct.normalized_map['pen_style'] == 'pen_style'


def test_filter_and_map_ai_tags_filters_device_for_cbd():
    ct = _make_tagger()
    suggested = ['Pen Style', '1000 mg', '10ml']
    mapped = ct._filter_and_map_ai_tags(suggested, forced_category='CBD', device_evidence=False)

    # should accept numeric mg tag but not 'pen_style' or 10ml
    assert '1000mg' in mapped
    assert all('pen' not in t for t in mapped)


def test_filter_and_map_ai_tags_allows_device_when_evidence():
    ct = _make_tagger()
    suggested = ['Pen Style', '1000 mg']
    mapped = ct._filter_and_map_ai_tags(suggested, forced_category='CBD', device_evidence=True)

    assert '1000mg' in mapped
    assert 'pen_style' in mapped
