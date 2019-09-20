import pytest
from joffrey import CLI, Group, errors

cli = CLI(systemexit=False)
cli.sc = Group(XOR=0)


@cli.arg()
def name(name):
    """Args, positional, are parsed in the order they're added in"""
    return name


@cli.sc.clump(AND='blah')
@cli.sc.flag(short='S')
def scream(text):
    """I have no mouth and I must ... yeah"""
    return text.upper()


@cli.sc.clump(AND='blah')
@cli.sc.flag('verbosity', namespace={'count': 0})
def verbose(nsp):
    """This does nothing but it shows namespaces (which are always passed as the first arg)"""
    if nsp.count < 10:
        nsp.count += 1
    return nsp.count


@cli.clump(XOR=0)
@cli.flag('addition')
def add(a: int = 4, *b: int):
    """Who needs a calculator"""
    return a + sum(b)


def test_ok_1():
    done = cli.parse('foo -S "test test" -vvvv')
    assert done.name == 'foo'
    assert done.scream == 'TEST TEST'
    assert done.verbosity == 4


def test_ok_2():
    done = cli.parse('bar -a 1 2 9')
    assert done.name == 'bar'
    assert done.addition == 1 + 2 + 9


def test_and_failure():
    with pytest.raises(errors.ANDError):
        cli.parse('foo -v')


def test_xor_failure():
    with pytest.raises(errors.XORError):
        cli.parse('foo --add 1 2 -S "ahh" -v')


def test_systemexit_still_works__just_in_case_yknow():
    with pytest.raises(SystemExit):
        cli.parse('foo --add 1 2 -S "ahh" -v', systemexit=True)
    with pytest.raises(SystemExit):
        cli.systemexit = True
        cli.parse('foo --add 1 2 -S "ahh" -v')


def test_namespaces_stateless():
    first = cli.parse('foo -S a -vvvv')
    second = cli.parse('foo -vvvv -S a')
    assert first.verbosity == second.verbosity == 4


def test_parser_namespace_attrs():
    nsp = cli.parse('foo -S aaa -v')
    assert (not nsp) is False
    assert nsp._.items() == vars(nsp).items()
    assert nsp.verbosity == nsp['verbosity']
