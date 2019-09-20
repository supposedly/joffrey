import pytest

from joffrey import CLI

cli = CLI(systemexit=False)


@cli.arg()  # n = 1
def first(value):
    return value


@cli.arg(2, namespace={'accum': []})
def floats(nsp, value):
    nsp.accum.append(value)
    return nsp.accum


@cli.arg(..., namespace={'count': 0})
def consumed(nsp, value):
    nsp.count += 1
    return nsp.count, value


def test_counts():
    n = cli.parse('one 2 3 c o n s u m e d')
    assert n == {'consumed': (8, 'd'), 'first': 'one', 'floats': ['2', '3']}


def test_strict():
    with pytest.raises(TypeError) as flag_exc_short:
        cli.parse('-x', strict=True)  # Unknown flag
    with pytest.raises(TypeError) as flag_exc_long:
        cli.parse('--ecks', strict=True)  # Unknown flag
    with pytest.raises(TypeError) as flag_exc_equals:
        cli.parse('-a=aaa', strict=True)  # Unknown flag
    assert str(flag_exc_short.value).startswith('Unknown flag')
    assert str(flag_exc_long.value).startswith('Unknown flag')
    assert str(flag_exc_equals.value).startswith('Unknown flag')


def test_too_many():
    cli.remove(consumed)
    with pytest.raises(TypeError) as arg_exc:
        cli.parse('fine fine fine BAD', strict=True)  # Too many args
    assert str(arg_exc.value).startswith('Too many positional')
