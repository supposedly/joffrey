import ergo
import pytest


@ergo.simple
def main(a: int, *b: list, c: set):
    return a, b, c


@ergo.simple.command
def fff(one: str.upper, *, two: lambda x: tuple(map(int, x))):
    return one, two


def test_simple():
    assert ergo.simple.run('1 2 3 4 --c 5') == (1, (['2'], ['3'], ['4']), {'5'})


def test_simple_cmd():
    assert fff.run('one -t 234') == ('ONE', (2, 3, 4))


simple2 = type(ergo.simple)()

@simple2(_='.', short_flags=False)
def main2(*, as_df):
    return as_df


def test_delayed_simple_config():
    assert simple2.run('--as.df 3') == '3'
    with pytest.raises(TypeError):
        simple2.run('-a 3')
