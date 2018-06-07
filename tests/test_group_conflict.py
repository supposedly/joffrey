import pytest
from ergo import Parser, errors

parser = Parser()
parser.group('sc', XOR=0)

@parser.arg()
def sc(a):
    pass
