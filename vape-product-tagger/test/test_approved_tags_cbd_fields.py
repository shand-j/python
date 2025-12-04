import json
from pathlib import Path


def test_approved_tags_contains_cbd_fields():
    p = Path(__file__).parents[1] / 'approved_tags.json'
    assert p.exists()
    data = json.loads(p.read_text())

    assert 'cbd_form' in data
    assert 'cbd_type' in data

    assert data['cbd_form'].get('applies_to') == ['CBD']
    assert 'tincture' in data['cbd_form'].get('tags', [])

    assert data['cbd_type'].get('applies_to') == ['CBD']
    assert 'full_spectrum' in data['cbd_type'].get('tags', [])
