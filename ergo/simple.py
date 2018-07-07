import inspect
import sys

from .core import CLI
from .misc import _Null, ErgoNamespace, convert


def _callable(obj):
    return callable(obj) and obj is not inspect._empty


class SimpletonBase:
    def __init__(self, cli=None, *, _='-', no_help=False, short_flags=True):
        self.cli = cli or CLI(no_help=no_help)
        self.underscore = _
        self.no_help = no_help
        self.short_flags = short_flags
        
        self._params = None
        self._callback = None
        self._consuming = False
        self.used = False
        self.commands = {}
    
    @staticmethod
    def _null_check(val):
        return val is _Null or val is inspect._empty

    def _add_flargs(self, cli, pos, flags):
        for arg in pos:
            if arg.kind == inspect.Parameter.VAR_POSITIONAL:
                def __hidden(arg):
                    def __(nsp, value):
                        nsp.accum.append(convert(arg.annotation, value))
                        return nsp.accum
                    __.__name__ = arg.name
                    return __
                cli.arg(
                  Ellipsis,
                  namespace={'accum': []},
                  required=False,
                  default=_Null if self._null_check(arg.default) else arg.default,
                )(__hidden(arg))
            else:
                def __hidden(arg):
                    def __(value):
                        return convert(arg.annotation, value)
                    __.__name__ = arg.name
                    return __
                cli.arg(
                  required=self._null_check(arg.default),
                  default=_Null if self._null_check(arg.default) else arg.default,
                )(__hidden(arg))
        
        for flag in flags:
            def __hidden(flag):
                def __(value):
                    return convert(flag.annotation, value)
                __.__name__ = flag.name
                return __
            cli.flag(
              short=_Null if self.short_flags else None,
              default=_Null if self._null_check(flag.default) else flag.default,
              _=self.underscore
            )(__hidden(flag))
    
    def command(self, func):
        cmd = self.commands[func.__name__] = SimpleCommand(
          func,
          self.cli.command(func.__name__),
          _=self.underscore,
          no_help=self.no_help,
          short_flags=self.short_flags
        )
        return cmd


class SimpleCommand(SimpletonBase):
    def __init__(self, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.used:
            raise ValueError('Cannot have more than one function per simple command/CLI')
        self.used = True
        
        self._callback = func
        self._params = inspect.signature(func).parameters.values()
        
        pos = [i for i in self._params if i.kind <= inspect.Parameter.VAR_POSITIONAL]
        flags = [i for i in self._params if i.kind == inspect.Parameter.KEYWORD_ONLY]
        self._consuming = pos and pos[-1].kind == inspect.Parameter.VAR_POSITIONAL
        self._add_flargs(self.cli, pos, flags)
    
    def __call__(self, *args, **flags):
        if not args:  # allow to be called normally as well
            args = [
              flags.pop(p.name, ())
                if p.kind == inspect.Parameter.VAR_POSITIONAL
              else flags.pop(p.name)
                if p.name in flags or p.default is inspect._empty else p.default
              for p in self._params
              if p.kind <= inspect.Parameter.VAR_POSITIONAL
              ]
            if self._consuming:
                args.extend(args.pop(-1))
        return self._callback(*args, **flags)
    
    def run(self, inp=None):
        nsp = self.cli.parse(inp)
        flargs = {}
        for name, val in nsp._.items():
            if isinstance(val, ErgoNamespace):
                self.commands[name](**dict(val._.items()))
                continue
            flargs[name] = val
        return self(**flargs)


class Simpleton(SimpletonBase):
    def __call__(self, func=None, *, _='-', no_help=False, short_flags=True):
        """Either secondary __init__() (ew, ish) or normal deco"""
        if func is None:
            self.underscore = _
            self.short_flags = short_flags
            self.no_help = no_help
            if no_help:
                try:
                    self.cli.remove('help')
                except KeyError:
                    pass
            return self
        
        if self.used:
            raise ValueError('Cannot have more than one function per simple command/CLI')
        self.used = True
        
        self._callback = func
        self._params = inspect.signature(func).parameters.values()
        
        pos = [i for i in self._params if i.kind <= inspect.Parameter.VAR_POSITIONAL]
        flags = [i for i in self._params if i.kind == inspect.Parameter.KEYWORD_ONLY]
        self._consuming = pos and pos[-1].kind == inspect.Parameter.VAR_POSITIONAL
        self._add_flargs(self.cli, pos, flags)
        return self
    
    def call(self, **flags):
        args = [
          flags.pop(p.name, ())
            if p.kind == inspect.Parameter.VAR_POSITIONAL
          else flags.pop(p.name)
            if p.name in flags or p.default is inspect._empty else p.default
          for p in self._params
          if p.kind <= inspect.Parameter.VAR_POSITIONAL
          ]
        if self._consuming:
            args.extend(args.pop(-1))
        return self._callback(*args, **flags)
    
    def run(self, inp=None):
        nsp = self.cli.parse(inp)
        flargs = {}
        for name, val in nsp._.items():
            if isinstance(val, ErgoNamespace):
                self.commands[name](**dict(val._.items()))
                continue
            flargs[name] = val
        return self.call(**flargs)


sys.modules[__name__] = Simpleton()
