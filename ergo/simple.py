import inspect
import sys

from .core import CLI
from .misc import _Null, ErgoNamespace


def _callable(obj):
    return callable(obj) and obj is not inspect._empty


class Simpleton:
    used = False

    def __init__(self, cli=None, *, _='-', no_help=False, short_flags=True):
        self.cli = cli or CLI()
        self.underscore = _
        self.no_help = no_help
        self.short_flags = short_flags
        
        self.commands = {}
        self.callback = None
    
    def __call__(self, func=None, *, _='-', no_help=False, short_flags=True):
        """Either secondary __init__() (ew, ish) or normal deco"""
        if func is None:
            self.underscore = _
            self.no_help = no_help
            self.short_flags = short_flags
            return self
        
        if self.used:
            raise ValueError('Cannot have more than one function per simple command/CLI')
        
        self.used = True
        self.callback = func
        params = inspect.signature(func).parameters.values()
        
        pos = [i for i in params if i.kind <= inspect.Parameter.VAR_POSITIONAL]
        flags = [i for i in params if i.kind == inspect.Parameter.KEYWORD_ONLY]
        if pos[-1].kind == inspect.Parameter.VAR_POSITIONAL:
            ###### TODO: ***REMOVED***
            pass
        self._add_flargs(self.cli, pos, flags)

        return self

    def _add_flargs(self, cli, pos, flags):
        for arg in pos:
            def __(value):
                return arg.annotation(value) if _callable(arg.annotation) else value
            __.__name__ = arg.name
            cli.arg(
              ... if arg.kind == inspect.Parameter.VAR_POSITIONAL else 1,
              required=(arg.default == _Null),
              default=_Null if arg.default == _Null else arg.default,
              )(__)
        
        for flag in flags:
            def __(value):
                return flag.annotation(value) if _callable(flag.annotation) else value
            __.__name__ = flag.name
            cli.flag(
              short=_Null if self.short_flags else None,
              default=_Null if arg.default == _Null else arg.default,
              _=self.underscore
              )(__)
    
    def command(self, func):
        cmd = self.commands[func.__name__] = Simpleton(
          self.cli.command(func.__name__),
          _=self.underscore,
          no_help=self.no_help,
          short_flags=self.short_flags
          )(func)
        return cmd
    
    def run(self, inp=None):
        nsp = self.cli.parse(inp)
        flargs = {}
        for name, val in nsp._.items():
            if isinstance(val, ErgoNamespace):
                self.commands[name].callback(**dict(val._.items()))
                continue
            flargs[name] = val
        return self.callback(**flargs)


sys.modules[__name__] = Simpleton()
