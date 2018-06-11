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
    with pytest.raises(TypeError):
        parser.parse('-x', strict=True)  # Unknown flag
    with pytest.raises(TypeError):
        parser.parse('one', strict=True)  # Too few args


def test_too_many():
    parser.remove(consumed)
    with pytest.raises(TypeError):
        parser.parse('fine fine fine BAD', strict=True)  # Too many args
