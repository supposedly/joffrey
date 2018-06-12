import pytest

from ergo import Parser

parser = Parser(systemexit=False)


@parser.arg()  # n = 1
def first(value):
    return value


@parser.arg(2, namespace={'accum': []})
def floats(nsp, value):
    nsp.accum.append(value)
    return nsp.accum


@parser.arg(..., namespace={'count': 0})
def consumed(nsp, value):
    nsp.count += 1
    return nsp.count, value


def test_counts():
    n = parser.parse('one 2 3 c o n s u m e d')
    assert n == {'consumed': (8, 'd'), 'first': 'one', 'floats': ['2', '3']}


def test_strict():
    with pytest.raises(TypeError) as arg_exc:
        parser.parse('one', strict=True)  # Too few args
    with pytest.raises(TypeError) as flag_exc:
        parser.parse('one two three -x', strict=True)  # Unknown flag
    assert str(arg_exc.value).startswith('Too few positional')
    assert str(flag_exc.value).startswith('Unknown flag')


def test_too_many():
    parser.remove(consumed)
    with pytest.raises(TypeError) as arg_exc:
        parser.parse('fine fine fine BAD', strict=True)  # Too many args
    assert str(arg_exc.value).startswith('Too many positional')
