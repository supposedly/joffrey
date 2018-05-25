from ergo import Parser

parser = Parser()
parser.group('sc', XOR=0)


@parser.arg()
def name(name):
    """Args, positional, are parsed in the order they're added in"""
    return name


@parser.sc.clump(AND='blah')  # nothing special about the rvalues here as long as they're unique to their clump
@parser.sc.flag(short='S')
def scream(text):
    """I have no mouth and I must ... yeah"""
    return text.upper()


@parser.sc.clump(AND='blah')  # this flag and `scream` *must* appear together (same AND)
@parser.sc.flag('verbosity', namespace={'count': 0})
def verbose(nsp):
    """This does nothing but it shows namespaces (which are always passed as the first arg)"""
    if nsp.count < 5:
        nsp.count += 1
    return nsp.count


@parser.clump(XOR=0)  # this flag *cannot* appear alongside `scream` (same XOR)
@parser.flag('addition')
def add(a: int, b: int = 0):  # can also provide default args if needed
    """Who needs a calculator"""
    return a + b


print(parser.parse())
