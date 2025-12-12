from main import ControlledTagger


def test_rule_based_does_not_add_device_style_for_cbd():
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)

    handle = 'cbdna-1000mg-full-spectrum-cbd-oil-10ml'
    title = 'CbdNa full spectrum 1000mg oil 10ml'
    description = 'Natural CBD oil 1000 mg per bottle'

    rule_tags, forced = ct.get_rule_based_tags(handle, title, description, product_type='CBD')

    assert forced == 'CBD'
    assert 'pen_style' not in rule_tags
