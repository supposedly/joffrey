import pytest
from ergo import Parser, errors


parser = Parser(systemexit=False)
parser.group('sc', XOR=0)


@parser.arg()
def name(name):
    """Args, positional, are parsed in the order they're added in"""
    return name


@parser.sc.clump(AND='blah')
@parser.sc.flag(short='S')
def scream(text):
    """I have no mouth and I must ... yeah"""
    return text.upper()


@parser.sc.clump(AND='blah')
@parser.sc.flag('verbosity', namespace={'count': 0})
def verbose(nsp):
    """This does nothing but it shows namespaces (which are always passed as the first arg)"""
    if nsp.count < 10:
        nsp.count += 1
    return nsp.count


@parser.clump(XOR=0)
@parser.flag('addition')
def add(a, *b):
    """Who needs a calculator"""
    return int(a) + sum(map(int, b))


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
    with pytest.raises(errors.ANDError):
        parser.parse('foo -v')


def test_xor_failure():
    with pytest.raises(errors.XORError):
        parser.parse('foo --add 1 2 -S "ahh" -v')


def test_systemexit_still_works__just_in_case_yknow():
    with pytest.raises(SystemExit):
        parser.parse('foo --add 1 2 -S "ahh" -v', systemexit=True)
    with pytest.raises(SystemExit):
        parser.systemexit = True
        parser.parse('foo --add 1 2 -S "ahh" -v')


def test_namespaces_stateless():
    first = parser.parse('foo -S a -vvvv')
    second = parser.parse('foo -vvvv -S a')
    assert first.verbosity == second.verbosity == 4
