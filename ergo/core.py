"""
argparse sucks
this sucks too but less
"""
import os
import sys


_FILE = os.path.basename(sys.argv[0])
_Null = type('_NullType', (), {'__slots__': (), '__repr__': lambda self: '<_Null>'})()


class Parser:
    pass


class Group:
    pass
