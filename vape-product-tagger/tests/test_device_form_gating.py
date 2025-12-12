import logging

from modules.product_tagger import ProductTagger


def _make_tagger():
    logger = logging.getLogger('test')
    logger.addHandler(logging.NullHandler())
    return ProductTagger(config=None, logger=logger, ollama_processor=None)


def test_device_form_not_applied_to_cbd_items():
    tagger = _make_tagger()
    product = {
        'title': 'Realest CBD 1000mg oil 30ml',
        'description': 'Full spectrum CBD oil with natural terpenes'
    }

    # Device form should not be returned for a CBD product that has no device evidence
    forms = tagger.tag_device_form(product)
    assert forms == []


def test_device_form_applied_for_device_products():
    tagger = _make_tagger()
    product = {
        'title': 'Sleek Pen Vape Device 2ml',
        'description': 'Slim pen style vape kit with prefilled pods'
    }

    forms = tagger.tag_device_form(product)
    assert isinstance(forms, list)
    assert any('Pen' in t or 'pen' in t.lower() for t in forms)
