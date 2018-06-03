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

from .misc import multiton, typecast, ErgoNamespace
from .clumps import And, Or, Xor, ClumpGroup


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
        self._args = ' '.join(map(str.upper, params))
        self.argcount = sys.maxsize if any(i.kind == 2 for i in params.values()) else len(params)
        self.func = func
        self.callback = typecast(func)
        self.help = func.__doc__
        self.name = name or func.__name__
        self.namespace = None if namespace is None else SimpleNamespace(**namespace)
        self.AND = self.OR = self.XOR = _Null
    
    def __call__(self, *args, **kwargs):
        if self.namespace is None:
            return self.callback(*args, **kwargs)
        return self.callback(self.namespace, *args, **kwargs)
    
    def __str__(self):
        return "`{}'".format(self.name)
    
    def clear_nsp(self):
        vars(self.namespace).clear()


@multiton(cls=Entity, kw=False)
class Flag(Entity.cls):
    def __init__(self, *args, **kwargs):
        self.short = None
        super().__init__(*args, **kwargs)
    
    def __str__(self):
        if self.short is None:
            return '[--{} {}]'.format(self.name, self._args)
        return '[-{} | --{} {}]'.format(self.short, self.name, self._args)


class Helper:
    @property
    def all_commands(self):
        return (*self.commands, *(name for g in self._groups for name in g.commands))
    
    @property
    def all_flags(self):
        return (*self.flags.values(), *(entity for g in self._groups for entity in g.flags.values()))
    
    @property
    def all_args(self):
        return self.args.values()
    
    @property
    def usage(self):
        return '{}{} {} {}'.format(
          _FILE,
          str(self),
          ' '.join(map(str, self.all_flags)),
          ' '.join(map(str, self.all_args)),
          )
    
    @property
    def help(self):
        return '\n'.join(
          '{}\n{}'.format(
            label.upper(),
            '\n'.join({
              '\t{: <15} {}'.format(i.name, i.help)
              for i in getattr(self, 'all_' + label)
            }),
          )
          for label in ('args', 'flags')
        )
    
    def format_help(self, usage=True, commands=True):
        built = ['']
        if usage:
            built.append('usage: {}'.format(self.usage))
        if commands and self.commands:
            built.append('subcommands: {}'.format(','.join(map(str, self.all_commands))))
        if usage or commands:
            built.append('')
        built.append(self.help)
        return '\n'.join(built)
    
    def print_help(self, usage=True, commands=True):
        print(self.format_help(usage, commands), end='\n\n')


class _Handler:
    def __init__(self):
        self.args = {}
        self.commands = {}
        self.flags = {}
        self._aliases = {}
        self._defaults = {}
        
        self._and = ClumpGroup()
        self._or = ClumpGroup()
        self._xor = ClumpGroup()
        
        self._required = set()
    
    def __repr__(self):
        quote = "'" if hasattr(self, 'name') else ''
        return '<{c}{s}{q}{n}{q}>'.format(
          c=self.__class__.__name__,
          n=getattr(self, 'name', ''),
          s=' ' if hasattr(self, 'name') else '',
          q=quote,
          )
    
    @property
    def parent_and(self):
        return self._and
    
    @property
    def parent_or(self):
        return self._or
    
    @property
    def parent_xor(self):
        return self._xor
    
    @property
    def _req_names(self):
        return {e.name for e in self._required}
    
    def getflag(self, name):
        try:
            return self.flags[name]
        except KeyError:
            return self.flags[self._aliases[name]]
    
    def hasflag(self, name):
        return name in self.flags or self._aliases.get(name, _Null) in self.flags
    
    def getcmd(self, name):
        try:
            return self.commands[name]
        except KeyError:
            return self.commands[self._aliases[name]]
    
    def hascmd(self, name):
        return name in self.commands or self._aliases.get(name, _Null) in self.commands
    
    def hasany(self, name):
        return self.hasflag(name) or self.hascmd(name) or name in self.args or self._aliases.get(name, _Null) in self.args
    
    def _clump(self, obj, AND, OR, XOR):
        obj.AND = AND
        obj.OR = OR
        obj.XOR = XOR
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
        parsed = {self._aliases.get(i, i) for i in parsed}
        AND_SUC = set(self.parent_and.successes(parsed))
        OR_SUC = set(self.parent_or.successes(parsed))
        XOR_SUC = set(self.parent_xor.successes(parsed))
        
        for all_failed, received in self.parent_and.failures(parsed):
            # AND failure == member of an AND clump that was not given
            # an AND failure is okay if it's in a satisfied OR clump (i.e. there's at least one other OR in its clump that was given)
            # or if it's in a satisfied XOR clump (i.e. exactly one other XOR in its clump was given)
            not_exempt = (all_failed - received) - OR_SUC - XOR_SUC
            if not_exempt:
                raise TypeError(
                  'Expected all of the following flags/arguments: {}\nGot {}'.format(
                      ', '.join(map(repr, all_failed)),
                      ', '.join(map(repr, received)) or 'none'
                    )
                  )
        
        for all_failed, received in self.parent_or.failures(parsed):
            # OR failure == member of an OR clump where none were given
            # an OR failure is okay if it's in a satisfied XOR clump (i.e. exactly one other XOR in its clump was given)
            not_exempt = (all_failed - received) - XOR_SUC
            if not_exempt:
                raise TypeError(
                  'Expected at least one of the following flags/arguments: {}\nGot none'.format(
                      ', '.join(map(repr, received))
                    )
                  )
        
        for all_failed, not_received in self.parent_xor.failures(parsed):
            # XOR failure == member of an XOR clump that was given alongside at least one other
            # an XOR failure is okay if it satisfies an AND clump (i.e. all other ANDs in its clump were given)
            not_exempt = (all_failed - not_received) - AND_SUC - self._req_names
            if len(not_exempt) > 1:
                raise TypeError(
                  'Expected at most one of the following flags/arguments: {}\nGot {}'.format(
                      ', '.join(map(repr, all_failed)),
                      ', '.join(map(repr, all_failed - not_received))
                    )
                  )
        
        return True
    
    def clump(self, *, AND=_Null, OR=_Null, XOR=_Null):
        def inner(cb):
            entity = Entity(getattr(cb, 'func', cb))
            self._clump(entity, AND, OR, XOR)
            return entity
        return inner
    
    def arg(self, required=False):
        def inner(cb):
            entity = Entity(cb)
            if required:
                self._required.add(entity)
            self.args[entity.name] = entity
            return entity
        return inner
    
    def flag(self, dest=None, short=_Null, *, default=_Null, namespace=None, required=False):
        def inner(cb):
            entity = Flag(cb, namespace=namespace, name=dest)
            if short is not None:  # _Null == default, None == none
                entity.short = short or entity.name[0]
                self._aliases[entity.short] = entity.name
            if dest is not None:
                self._aliases[cb.__name__] = entity.name
            if default is not _Null:
                self._defaults[entity.name] = default
            if required:
                self._required.add(entity)
            self.flags[entity.name] = entity
            return entity
        return inner
    
    def command(self, name, *args, aliases=(), AND=_Null, OR=_Null, XOR=_Null, **kwargs):
        subparser = Subparser(*args, **kwargs, parent=self, name=name)
        for alias in aliases:
            self._aliases[alias] = name
        self._clump(subparser, AND, OR, XOR)
        self.commands[name] = subparser
        return subparser


class ParserBase(_Handler, Helper):
    def __init__(self, flag_prefix='-'):
        self.flag_prefix = flag_prefix
        self.long_prefix = 2 * flag_prefix
        self._groups = set()
        super().__init__()
    
    def getflag(self, name):
        try:
            return super().getflag(name)
        except KeyError:
            for g in self._groups:
                try:
                    return g.getflag(name)
                except KeyError:
                    pass
            raise
    
    def hasflag(self, name):
        return super().hasflag(name) or any(g.hasflag(name) for g in self._groups)
    
    def hasany(self, name):
        return super().hasflag(name) or super().hascmd(name) or name in self.args or self._aliases.get(name, _Null) in self.args
    
    def enforce_clumps(self, parsed):
        p = {next((g.name for g in self._groups if g.hasany(i)), self._aliases.get(i, i)) for i in parsed}
        self.p = p
        return super().enforce_clumps(p) and all(g.enforce_clumps(parsed) for g in self._groups)
    
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
            
            if value.startswith(self.long_prefix):
                if self.hasflag(value.lstrip(self.flag_prefix)):  # long
                    skip = self.getflag(value.lstrip(self.flag_prefix)).argcount
                    next_pos = next((i for i, v in enumerate(inp[idx:]) if v.startswith(self.flag_prefix)), len(inp))
                    if next_pos < skip:
                        skip = next_pos
                    flags.big.append((value.lstrip(self.flag_prefix), inp[idx:skip+idx]))
                continue
            
            for name in filter(self.hasflag, value[1:]):  # short
                skip = self.getflag(name).argcount
                next_pos = next((i for i, v in enumerate(inp[idx:]) if v.startswith(self.flag_prefix)), len(inp))
                if next_pos < skip:
                    skip = next_pos
                flags.small.append((name, inp[idx:skip+idx]))
        
        return [*flags.big, *flags.small], args
    
    def do_parse(self, inp=None, *, flargs=None):
        consumeds = set()
        parsed = {}
        flags, positionals = self._extract_flargs(inp) if flargs is None else flargs
        
        for idx, (flag, args) in enumerate(flags):
            if self.hasflag(flag):
                consumeds.add(idx)
                entity = self.getflag(flag)
                parsed[flag] = entity(*args)
        flags[:] = [v for i, v in enumerate(flags) if i not in consumeds]
        
        consumeds.clear()
        for idx, (value, (name, arg)) in enumerate(zip(positionals, self.args.items())):
            consumeds.add(idx)
            if self.hascmd(value):
                parsed[self._aliases.get(value, value)] = self.getcmd(value).do_parse(flargs=(flags, positionals))
                continue
            parsed[name] = arg(value)
        positionals[:] = [v for i, v in enumerate(positionals) if i not in consumeds]
        
        self.enforce_clumps(parsed)
        # FIXME: This is pretty bad
        parsed = {self._aliases.get(k, k) if self.hasany(k) else next(g._aliases.get(k, k) for g in self._groups if g.hasany(k)): v for k, v in parsed.items()}
        return ErgoNamespace(**{**self._defaults, **parsed})
    
    def parse(self, inp=None):
        try:
            return self.do_parse(inp)
        except TypeError as e:
            self.print_help()
            raise SystemExit(e if str(e) else type(e))
    
    def group(self, name, *, required=False, AND=_Null, OR=_Null, XOR=_Null):
        if name in vars(self):
            raise ValueError('Group name already in use for this parser: ' + name)
        if iskeyword(name) or not name.isidentifier():
            raise ValueError('Invalid group name: ' + name)
        group = Group(self, name)
        if required:
            self._required.add(group)
        self._clump(group, AND, OR, XOR)
        setattr(self, name, group)
        self._groups.add(group)
        return group


class SubHandler(_Handler):
    def __init__(self, parent, name):
        self.name = name
        self.parent = parent
        self.AND = self.OR = self.XOR = _Null
        super().__init__()
    
    @property
    def parent_and(self):
        return ClumpGroup({*self._and, *self.parent.parent_and})
    
    @property
    def parent_or(self):
        return ClumpGroup({*self._or, *self.parent.parent_or})
    
    @property
    def parent_xor(self):
        return ClumpGroup({*self._xor, *self.parent.parent_xor})


class Group(SubHandler):
    def arg(self, required=False):
        def inner(cb):
            entity = Entity(cb)
            if required:
                self._required.add(entity)
            self.args[entity.name] = entity
            return self.parent.arg(required)(entity.func)
        return inner


class Subparser(SubHandler, ParserBase):
    def __init__(self, flag_prefix='-', *, parent, name):
        SubHandler.__init__(self, parent, name)
        ParserBase.__init__(self, flag_prefix)
    
    def __str__(self):
        return ' {}'.format(self.name)
    

class Parser(ParserBase):
    def parse(self, inp=sys.argv[1:]):
        if isinstance(inp, str):
            inp = shlex.split(inp)
        return super().parse(list(inp))  # copy input
    
    def __str__(self):
        return ''
