import pytest

from ergo import CLI, Group


@pytest.fixture
def cli():
    return CLI()


def test_empty_flag_prefix():
    with pytest.raises(ValueError):
        CLI(flag_prefix='')


def test_underscore_kwarg(cli):
    @cli.flag()
    def oh_hi():
        pass
    assert 'oh_hi' in cli.parse('--oh-hi')


def test_change_underscore(cli):
    cli.flag('oh_hi')(lambda: None)
    cli.flag('oh_hello', _='.')(lambda: None)
    
    assert 'oh_hello' in cli.parse('--oh.hello')
    assert 'oh_hello' in cli.parse('-e')  # next untaken alphanumeric alias
    assert 'oh_hi' in cli.parse('-o')


def test_bad_group_names(cli):
    cli.name_conflict = Group()
    with pytest.raises(ValueError):
        cli.name_conflict = Group()


def test_nonexistents(cli):
    for x in ('remove', 'getarg', 'getflag', 'getcmd'):
        with pytest.raises(KeyError):
            getattr(cli, x)('this does not exist')
    assert not cli.hasany('this also does not exist')
