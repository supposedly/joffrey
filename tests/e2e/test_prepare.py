import pytest

from kizbra import CLI

@pytest.fixture
def cli():
    cli = CLI()

    @cli.flag(default=3)
    def flag(value):
        return value


    @cli.arg(default=2)
    def arg(value):
        return value
    
    return cli


def test_cli_result(cli):
    assert cli.result == {'flag': 3, 'arg': 2}
    cli.prepare('--flag 2 3')
    assert cli.result == {'flag': '2', 'arg': '3'}


def test_defaults(cli):
    assert cli.prepare('--flag 2').set_defaults(flag=6, arg=7).result == {'flag': '2', 'arg': 7}
