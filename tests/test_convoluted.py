import pytest
from ergo import Parser, errors

parser = Parser(systemexit=False)
parser.group('grp_0', XOR=0)
preview = parser.command('preview', XOR=0, OR=0)


@parser.grp_0.clump(AND=0)
@parser.arg(required=True)
def infile(path):
    return path


@parser.clump(OR=0)
@parser.grp_0.clump(AND=0)
@parser.grp_0.arg()
def outdir(path):
    return path


@parser.grp_0.flag(short='t', default='')
def header(text=''):
    return text


@parser.grp_0.flag(short='s', default=False)
def comment_src():
    return True


@parser.clump(XOR=0)
@parser.flag(short='f', default=None)
def find(transition):
    return transition


@parser.flag('verbosity', short='v', namespace={'count': 0}, default=0)
def verbose(nsp):
    return nsp.count


@preview.arg(required=True)
def transition(tr):
    return tr


@preview.flag(short='n', default='eh')
def first(value):
    return value


@preview.flag(short='o', default='?')
def state(num):
    return num


def test_no_and_failure():
    """This (disregarding equals vs space) used to not work"""
    a = parser.parse('foo -f 10')
    b = parser.parse('foo -f=10')
    assert a == b


def test_clump_failures():
    with pytest.raises(errors.RequirementError):
        parser.parse('-f 10')
    with pytest.raises(errors.ANDError):
        parser.parse('foo -t')
    with pytest.raises(errors.ORError):
        parser.parse('foo -tf 10')  # not XORError because grp_0 is parsed first


def test_subparser_clump_failure():
    with pytest.raises(errors.XORError):
        parser.parse('foo -t 10 preview 10')


def test_ok():
    parser.parse('foo preview 10')
    parser.parse('foo bar -t')


def test_subparser_flag_with_argument():
    done = parser.parse('foo preview 20 -o None')
    assert done.preview == {'transition': '20', 'state': 'None', 'first': 'eh'}
