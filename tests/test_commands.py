import pytest
from ergo import Parser, errors

parser = Parser(systemexit=False)
int_cmd = parser.command('int', XOR=0)
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


@int_cmd.arg()
def integer(num: int):
    """Wow a to-integer CLI"""
    return num


def test_ok_1():
    done = parser.parse('test')
    assert done.name == 'test'


def test_help():
        parser.format_help()  # codecov...
        with pytest.raises(SystemExit):
            parser.help()
        with pytest.raises(SystemExit):
            parser.help('verbose')


def test_subparser_consumes_everything():
    first = parser.parse('test int 1')
    second = parser.parse('int 1 test')
    assert first.int == second.int
    # in pre-0.1.5 versions, these would AssertionError because `int` wouldn't consume `test`
    assert 'name' not in second
    assert first != second


def test_subparser_xor_failure():
    for infix in ('-S nothin', '-v', '-S nothin -v'):
        with pytest.raises(errors.XORError):
            parser.parse('test {} int 1'.format(infix))


def test_arg_failure():
    with pytest.raises(TypeError):
        parser.parse('test -S')


def test_conv_failure():
    with pytest.raises(ValueError):
        parser.parse('test int what')
