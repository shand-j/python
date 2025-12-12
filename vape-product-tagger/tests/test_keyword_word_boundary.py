import logging

from modules.product_tagger import ProductTagger


def _make_tagger():
    # minimal stub logger and config — _match_keywords doesn't need config
    logger = logging.getLogger('test')
    logger.addHandler(logging.NullHandler())
    return ProductTagger(config=None, logger=logger, ollama_processor=None)


def test_keyword_word_boundary_no_false_positive():
    tagger = _make_tagger()
    text = "This will happen soon"
    assert not tagger._match_keywords(text, ["pen"])


def test_keyword_word_boundary_positive_match():
    tagger = _make_tagger()
    text = "Slim pen device for on-the-go"
    assert tagger._match_keywords(text, ["pen"]) is True


def test_keyword_plural_matching():
    tagger = _make_tagger()
    text = "These sticks are durable"
    assert tagger._match_keywords(text, ["stick"]) is True
