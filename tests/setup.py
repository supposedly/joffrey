from ergo import Parser

parser = Parser()
parser.group('sc', XOR=0)
parser.sc: None


def name(name):
    """Args, positional, are parsed in the order they're added in"""
    return name


def scream(text):
    """I have no mouth and I must ... yeah"""
    return text.upper()


def verbose(nsp):
    """This does nothing but it shows namespaces (which are always passed as the first arg)"""
    if nsp.count < 10:
        nsp.count += 1
    return nsp.count


def add(a, *b):
    """Who needs a calculator"""
    return int(a) + sum(map(int, b))
