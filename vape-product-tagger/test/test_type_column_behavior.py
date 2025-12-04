from main import ControlledTagger


def test_type_column_cbd_strength_from_type():
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)

    handle = 'test-cbd-1000mg'
    title = '1000mg bottled wellness'
    description = 'A natural wellness product'

    rule_tags, forced = ct.get_rule_based_tags(handle, title, description, product_type='CBD')

    assert forced == 'CBD'
    assert any(tag.endswith('mg') for tag in rule_tags)


def test_type_column_vaping_allows_device_form_without_style_word():
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)

    handle = 'test-vape-pen'
    title = 'Sleek pen device 2ml'
    description = 'Slim pen with prefilled pods'

    rule_tags, forced = ct.get_rule_based_tags(handle, title, description, product_type='Vaping Products')

    assert 'pen_style' in rule_tags
