from ergo import CLI
cli = CLI()


@cli.flag()
def flag(value):
    return value


@cli.arg()
def arg(value):
    return value


def test_double_dash():
    assert cli.parse('--flag FOO -- --flag') == {'flag': 'FOO', 'arg': '--flag'}
