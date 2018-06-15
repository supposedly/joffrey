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
    assert 'oh_hi' in parser.parse('--oh-hi')


def test_change_underscore(parser):
    parser.flag('oh_hi')(lambda: None)
    parser.flag('oh_hello', _='.')(lambda: None)
    
    assert 'oh_hello' in parser.parse('--oh.hello')
    assert 'oh_hello' in parser.parse('-e')  # next untaken alphanumeric alias
    assert 'oh_hi' in parser.parse('-o')


def test_bad_group_names(parser):
    with pytest.raises(ValueError):
        parser.group('def')
    with pytest.raises(ValueError):
        parser.group('not an identifier')
    parser.group('name_conflict')
    with pytest.raises(ValueError):
        parser.group('name_conflict')


def test_nonexistents(parser):
    parser.group('for_codecov')  # causes the `for g in self._groups` loops to run
    for x in ('remove', 'getarg', 'getflag', 'getcmd'):
        with pytest.raises(KeyError):
            getattr(parser, x)('this does not exist')
    assert not parser.hasany('this also does not exist')