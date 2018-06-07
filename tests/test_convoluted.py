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


@preview.flag(short='n', default='Moore')
def neighborhood(value):
    return value


@preview.flag(short='o', default='?')
def states(num):
    return str(num)


def test_no_and_failure():
    """This used to not work"""
    parser.parse('one -f 10')


def test_or_failure():
    with pytest.raises(errors.ErgoException):
        parser.parse('-f 10')
