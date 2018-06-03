"""
argparse sucks
this sucks too but less
"""
import inspect
import os
import sys
import shlex
from keyword import iskeyword
from types import SimpleNamespace

from .misc import ErgoNamespace, multiton, typecast
from .clumps import And, Or, Xor


_FILE = os.path.basename(sys.argv[0])
_Null = type(
  '_NullType', (),
  {
    '__bool__': lambda self: False,
    '__repr__': lambda self: '<_Null>',
  }
  )()


@multiton(kw=False)
class Entity:
    def __init__(self, func, *, name=None, namespace=None):
        params = inspect.signature(func).parameters
        self.callback = typecast(func)
        self.argcount = sys.maxsize if any(i.kind == 2 for i in params.values()) else len(params)
        self.help = func.__doc__
        self.name = name or func.__name__
        self.namespace = None if namespace is None else SimpleNamespace(**namespace)
        self.used = False
    
    def __call__(self, *args, **kwargs):
        if self.namespace is None:
            return self.callback(self.namespace, *args, **kwargs)
        return self.callback(*args, **kwargs)


class _Handler:
    def __init__(self):
        self.args = {}
        self.commands = {}
        self.flags = {}
        self._aliases = {}
        self._defaults = {}
        
        self._and = set()
        self._or = set()
        self._xor = set()
        
        self._required = set()
    
    @property
    def _req_names(self):
        return {e.name for e in self._required}
    
    def _getflag(self, name):
        try:
            return self.flags[name]
        except KeyError:
            return self.flags[self._aliases[name]]
    
    def _getsubcommand(self, name):
        try:
            return self.commands[name]
        except KeyError:
            return self.commands[self._aliases[name]]
    
    def _clump(self, obj, AND, OR, XOR):
        if AND is not _Null:
            self._and.add(And(AND, self))
            And(AND, self).add(obj)
        if OR is not _Null:
            self._or.add(Or(OR, self))
            Or(OR, self).add(obj)
        if XOR is not _Null:
            self._xor.add(Xor(XOR, self))
            Xor(XOR, self).add(obj)
    
    def enforce_clumps(self, parsed):
        return \
          all(c.verify(parsed) for g in (self._and, self._or, self._xor) for c in g) \
          and \
          not self._req_names.difference(self._aliases.get(name, name) for name in parsed)

    def clump(self, *, AND=_Null, OR=_Null, XOR=_Null):
        def inner(cb):
            entity = Entity(cb)
            self._clump(entity, AND, OR, XOR)
            return entity
        return inner
    
    def arg(self, required=False):
        def inner(cb):
            entity = Entity(cb)
            if required:
                self._required.add(entity)
            return entity
        return inner
    
    def flag(self, dest=None, short=_Null, *, default=_Null, namespace=None, required=False):
        def inner(cb):
            entity = Entity(cb, namespace=namespace)
            if dest is not None:
                self._aliases[entity.name] = dest
            if default is not _Null:
                self._defaults[entity.name] = default
            if short is not None:
                self._aliases[short or entity.name[0]] = entity.name
        return inner
    
    def command(self, name, *args, aliases=(), OR=_Null, XOR=_Null, AND=_Null, **kwargs):
        subparser = Subparser(*args, **kwargs, name=name)
        for alias in aliases:
            self._aliases[alias] = name
        self._clump(subparser, AND, OR, XOR)
        self.commands[name] = subparser
        return subparser


class Group(_Handler):
    def __init__(self, name):
        self.name = name
        super().__init__(self)
    
    def verfiy(self, parsed):
        return not self._req_names.difference(self._aliases.get(name, name) for name in parsed)


class ParserBase(_Handler):
    def __init__(self, flag_prefix='-'):
        self.flag_prefix = flag_prefix
        self.long_prefix = 2 * flag_prefix
        self._groups = {}
        super().__init__()
    
    def _extract_flargs(self, inp):
        flags = SimpleNamespace(big=[], small=[])
        args = []
        skip = 0
        
        for idx, value in enumerate(inp, 1):
            if skip > 0:
                skip -= 1
                continue
            
            if not value.startswith(self.flag_prefix) or value in (self.flag_prefix, self.long_prefix):
                args.append(value)
                continue
            
            skip = self._getflag(value).argcount
            next_pos = next((i for i, v in enumerate(inp[idx:], 1) if v.startswith(self.flag_prefix)), len(inp))
            if next_pos < skip + idx:
                skip = next_pos
            
            if value.startswith(self.long_prefix):
                flags.big.append((value.lstrip(self.flag_prefix), inp[idx:skip+idx]))
            else:
                for name in value[1:]:
                    flags.small.append((name, inp[idx:skip+idx]))
        
        return (*flags.big, *flags.small), args
    
    def parse(self, inp=None, *, _flargs=None):
        parsed = {}
        flags, positionals = _flargs if _flargs else self._extract_flargs(inp)
        
        for idx, (flag, arg_seqs) in enumerate(flags):
            if flag in self.flags:
                del flags[idx]
                flag.used = True
                for arg_seq in arg_seqs:
                    parsed[flag] = self._getflag(flag)(*arg_seq)
        
        for idx, (value, (name, arg)) in enumerate(zip(positionals, self.args.items())):
            del positionals[idx]
            arg.used = True
            name = self._aliases.get(value, value)
            if name in self.commands:
                parsed.update(self.commands[name].parse(_flargs=(flags, positionals)))
                continue
            parsed[name] = arg(value)
        
        self.enforce_clumps(parsed)
        return ErgoNamespace(**parsed)
    
    def enforce_clumps(self, parsed):
        return all(g.enforce_clumps(parsed) for g in self._groups) and super().enforce_clumps(parsed)

    def verify(self, parsed):
        return not self._req_names.difference(self._aliases.get(name, name) for name in parsed)
    
    def group(self, name, *, required=False, AND=_Null, OR=_Null, XOR=_Null):
        if name in vars(self):
            raise ValueError('Group name already in use for this parser: ' + name)
        if iskeyword(name) or not name.isidentifier():
            raise ValueError('Invalid group name: ' + name)
        group = Group(name)
        self._clump(group, AND, OR, XOR)
        if required:
            self._required.add(group)
        return group


class Parser(ParserBase):
    def parse(self, inp):
        if isinstance(inp, str):
            inp = shlex.split(inp)
        return super().parse(list(inp))  # copy input


class Subparser(ParserBase):
    def __init__(self, flag_prefix='-', *, name):
        self.name = name
        super().__init__()
