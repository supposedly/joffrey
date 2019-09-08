import pytest
from jeffrey import CLI, Group, errors

cli = CLI(systemexit=False)
cli.grp_0 = Group(XOR=0)
preview = cli.command('preview', XOR=0, OR=0)


@cli.grp_0.clump(AND=0)
@cli.arg(required=True)
def infile(path):
    return path


@cli.clump(OR=0)
@cli.grp_0.clump(AND=0)
@cli.grp_0.arg()
def outdir(path):
    return path


@cli.grp_0.flag(short='t', default='')
def header(text=''):
    return text


@cli.grp_0.flag(short='s', default=False)
def comment_src():
    return True


@cli.clump(XOR=0)
@cli.flag(short='f', default=None)
def find(transition):
    return transition


@cli.flag('verbosity', short='v', namespace={'count': 0}, default=0)
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
    a = cli.parse('foo -f 10')
    b = cli.parse('foo -f=10')
    assert a == b


def test_clump_failures():
    with pytest.raises(errors.RequirementError):
        cli.parse('-f 10')
    with pytest.raises(errors.ANDError):
        cli.parse('foo -t')
    with pytest.raises(errors.ORError):
        cli.parse('foo -tf 10')  # not XORError because grp_0 is parsed first


def test_subparser_clump_failure():
    with pytest.raises(errors.XORError):
        cli.parse('foo -t 10 preview 10')


def test_ok():
    cli.parse('foo preview 10')
    cli.parse('foo bar -t')


def test_subparser_flag_with_argument():
    done = cli.parse('foo preview 20 -o None')
    assert done.preview == {'transition': '20', 'state': 'None', 'first': 'eh'}
