import textwrap

from ergo.core import Parser


parser = Parser()
parser.nofind = parser.group('other_than_find', XOR='find')
preview = parser.command('preview')


@parser.arg()
def infile(path):
    """rueltabel-formatted input file"""
    return path


@parser.flag('verbosity', 'v', namespace={'count': 0})
def verbose(nsp):
    """Max x4 (repeat for more verbosity)"""
    if nsp.count < 4:
        nsp.count += 1
    return nsp.count


@parser.nofind.arg()
def outdir(path):
    """Directory to write output file to"""
    return path


@parser.nofind.flag(short='t')
def header(text=''):
    """Change or hide 'COMPILED FROM RUELTABEL' header"""
    return text or textwrap.dedent(
      '''\
      *********************************
      **** COMPILED FROM RUELTABEL ****
      *********************************
      '''
      )


@parser.nofind.flag(short='s', default=False)
def comment_src():
    """Comment each tabel source line above the final table line(s) it transpiles to"""
    return True


@parser.clump(XOR='find')
@parser.flag('match', short='f')
def find(tr):
    """Locate first transition in `infile` that matches"""
    return tr.split(',')


@preview.arg()
def transition(tr):
    return tr


print(parser.parse())