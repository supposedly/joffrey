import pytest
from ergo import Parser

from setup import name, scream, verbose, add


parser = Parser()
parser.group('sc', XOR=0)

parser.arg()(name)
parser.sc.clump(AND='blah')(parser.sc.flag(short='S')(scream))
parser.sc.clump(AND='blah')(parser.sc.flag('verbosity', namespace={'count': 0})(verbose))
parser.clump(XOR=0)(parser.flag('addition')(add))


def test_ok_1():
    done = parser.parse('foo -S "test test" -vvvv')
    assert done.name == 'foo'
    assert done.scream == 'TEST TEST'
    assert done.verbosity == 4


def test_ok_2():
    done = parser.parse('bar -a 1 2 9')
    assert done.name == 'bar'
    assert done.addition == 1 + 2 + 9


def test_and_failure():
    with pytest.raises(SystemExit):
        parser.parse('foo -v')


def test_xor_failure():
    with pytest.raises(SystemExit):
        parser.parse('foo --add 1 2 -S "oh no" -v')
