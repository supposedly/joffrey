import pytest
from ergo import CLI, Group, errors

cli = CLI(systemexit=False)
cli.sc = Group(XOR=0)
int_cmd = cli.command('int', XOR=0)


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


@int_cmd.arg()
def integer(num: int):
    """Wow a to-integer CLI"""
    return num


def test_ok_1():
    done = cli.parse('test')
    assert done.name == 'test'


def test_help():
        cli.format_help()  # codecov...
        with pytest.raises(SystemExit):
            cli.cli_help()
        with pytest.raises(SystemExit):
            cli.cli_help('verbose')
        with pytest.raises(SystemExit):
            cli.cli_help('int')  # gives help for int_cmd


def test_subparser_consumes_everything():
    first = cli.parse('test int 1')
    second = cli.parse('int 1 test')
    assert first.int == second.int
    # in pre-0.1.5 versions, these would AssertionError because `int` wouldn't consume `test`
    assert 'name' not in second
    assert first != second


def test_subparser_xor_failure():
    for infix in ('-S nothin', '-v', '-S nothin -v'):
        with pytest.raises(errors.XORError):
            cli.parse('test {} int 1'.format(infix))


def test_arg_failure():
    with pytest.raises(TypeError):
        cli.parse('test -S')


def test_conv_failure():
    with pytest.raises(ValueError):
        cli.parse('test int what')
