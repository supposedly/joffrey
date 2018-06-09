import pytest

from ergo import Parser


@pytest.fixture
def parser():
    return Parser()


def test_empty_flag_prefix():
    with pytest.raises(ValueError):
        Parser('')


def test_underscore_kwarg(parser):
    @parser.flag()
    def oh_hi():
        pass
    assert 'oh-hi' in parser.parse('--oh-hi')


def test_change_underscore(parser):
    parser.flag('oh_hi')(lambda: None)
    parser.flag('oh_hello', _='.')(lambda: None)
    
    assert 'oh.hello' in parser.parse('--oh.hello')
    assert 'oh.hello' in parser.parse('-e')  # next untaken alphanumeric alias
    assert 'oh-hi' in parser.parse('-o')
