from kizbra import CLI

cli = CLI()
cmd = cli.command('cmd')


@cli.flag()
def flag(value):
    return value


@cli.arg()
def arg(value):
    return value


@cmd.arg(...)
def arg_(value):
    return value


def test_double_dash():
    assert cli.parse('--flag FOO -- --flag') == {'flag': 'FOO', 'arg': '--flag'}


def test_propagate_args():
    assert cli.parse('an_argument cmd blah --flag=HEY bloh', strict=True, propagate_unknowns=True) == {'flag': 'HEY', 'arg': 'an_argument', 'cmd': {'arg_': 'bloh'}}
