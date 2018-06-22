import pytest

from ergo import Parser, Group


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
    parser.name_conflict = Group()
    with pytest.raises(ValueError):
        parser.name_conflict = Group()


def test_nonexistents(parser):
    parser.for_codecov = Group()  # causes the `for g in self._groups` loops to run
    for x in ('remove', 'getarg', 'getflag', 'getcmd'):
        with pytest.raises(KeyError):
            getattr(parser, x)('this does not exist')
    assert not parser.hasany('this also does not exist')
