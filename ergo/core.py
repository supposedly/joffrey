"""
argparse sucks
this sucks too but less
"""
import inspect
import os
import sys
import shlex
from itertools import chain
from keyword import iskeyword
from types import SimpleNamespace

from . import errors
from .misc import multiton, ErgoNamespace
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
        self._args = ' '.join([i.upper() for i in params][bool(namespace):])
        self.argcount = sys.maxsize if any(i.kind == 2 for i in params.values()) else len(params) - bool(namespace)
        self.callback = func
        self.help = func.__doc__ or ''
        self.name = name or func.__name__
        self.namespace = None if namespace is None else SimpleNamespace(**namespace)
        self._nsp = namespace
        self.AND = self.OR = self.XOR = _Null
    
    def __call__(self, *args, **kwargs):
        if self.namespace is None:
            return self.callback(*args, **kwargs)
        return self.callback(self.namespace, *args, **kwargs)
    
    def __str__(self):
        return "`{}'".format(self.name)
    
    def clear_nsp(self):
        if self.namespace is not None:
            vars(self.namespace).clear()
            vars(self.namespace).update(self._nsp)


@multiton(cls=Entity.cls, kw=False)
class Flag(Entity.cls):
    def __init__(self, *args, **kwargs):
        self.short = None
        super().__init__(*args, **kwargs)
    
    def __str__(self):
        space = ' ' if self._args else ''
        if self.short is None:
            return '[--{}{s}{}]'.format(self.name, self._args, s=space)
        return '[-{} | --{}{s}{}]'.format(self.short, self.name, self._args, s=space)


class HelperMixin:
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
        return '<{}{s}{q}{}{q}>'.format(
          self.__class__.__name__,
          getattr(self, 'name', ''),
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
    
    @property
    def entity_names(self):
        return set(chain(self.args, self.commands, self.flags))
    
    def dealias(self, name):
        return self._aliases.get(name, name)
    
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
    
    def enforce_clumps(self, parsed, groups=None):
        elim = {lbl.upper(): set(getattr(self, 'parent_'+lbl).successes(parsed)) for lbl in ('and', 'or', 'xor')}
        if groups is not None:
            g_dict = {g.name: g for g in groups}
            g_clumps = {lbl: {g_dict.get(i) for i in set(successes).intersection(g_dict)} for lbl, successes in elim.items()}
            g_clumps = {lbl: {name for g in groups for name in g.entity_names} for lbl, groups in g_clumps.items()}
            elim = {lbl: grp.union(succ) for lbl, succ, grp in zip(elim, elim.values(), g_clumps.values())}
        
        err_details = dict(
          AND_SUC=elim['AND'], OR_SUC=elim['OR'], XOR_SUC=elim['XOR'],
          parsed=parsed,
          groups=groups,
          handler=repr(self)
          )
        
        for all_failed, received in self._and.failures(parsed):
            # AND failure == member of an AND clump that was not given
            # an AND failure is okay if it's in a satisfied OR clump (i.e. there's at least one other OR in its clump that was given)
            # or if it's in a satisfied XOR clump (i.e. exactly one other XOR in its clump was given)
            not_exempt = (all_failed - received) - elim['OR'] - elim['XOR']
            if not_exempt:
                raise errors.ANDError(
                  'Expected all of the following flags/arguments: {}\nGot {}'.format(
                      ', '.join(map(repr, all_failed)),
                      ', '.join(map(repr, received)) or 'none'
                    ),
                  **err_details,
                  failed=all_failed, eliminating=received, not_exempt=not_exempt
                  )
        
        for all_failed, received in self._or.failures(parsed):
            # OR failure == member of an OR clump where none were given
            # an OR failure is okay if it's in a satisfied XOR clump (i.e. exactly one other XOR in its clump was given)
            not_exempt = (all_failed - received) - elim['XOR']
            if not_exempt:
                raise errors.ORError(
                  'Expected at least one of the following flags/arguments: {}\nGot none'.format(
                      ', '.join(map(repr, all_failed))
                    ),
                  **err_details,
                  failed=all_failed, eliminating=received, not_exempt=not_exempt
                  )
        
        for all_failed, not_received in self._xor.failures(parsed):
            # XOR failure == member of an XOR clump that was given alongside at least one other
            # an XOR failure is okay if it satisfies an AND clump (i.e. all other ANDs in its clump were given)
            not_exempt = (all_failed - not_received) - elim['AND'] - self._req_names
            if len(not_exempt) > 1:
                raise errors.XORError(
                  'Expected no more than one of the following flags/arguments: {}\nGot {}'.format(
                      ', '.join(map(repr, all_failed)),
                      ', '.join(map(repr, all_failed - not_received))
                    ),
                  **err_details,
                  failed=all_failed, eliminating=not_received, not_exempt=not_exempt
                  )
        
        return True
    
    def clump(self, *, AND=_Null, OR=_Null, XOR=_Null):
        def inner(cb):
            entity = Entity(cb.callback if isinstance(cb, Entity.cls) else cb)
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
            if dest is not None:
                self._aliases[cb.__name__] = entity.name
            if short is not None:  # _Null == default, None == none
                entity.short = short or entity.name[0]
                self._aliases[entity.short] = entity.name
            if default is not _Null:
                self._defaults[entity.name] = default
            if required:
                self._required.add(entity)
            self.flags[entity.name] = entity
            return entity
        return inner
    
    def command(self, name, *args, aliases=(), AND=_Null, OR=_Null, XOR=_Null, **kwargs):
        subparser = Subparser(*args, **kwargs, name=name, parent=self)
        for alias in aliases:
            self._aliases[alias] = name
        self._clump(subparser, AND, OR, XOR)
        self.commands[name] = subparser
        return subparser


class ParserBase(_Handler, HelperMixin):
    def __init__(self, flag_prefix='-', systemexit=True):
        self.flag_prefix = flag_prefix
        self.long_prefix = 2 * flag_prefix
        self.systemexit = systemexit
        self._groups = set()
        super().__init__()
    
    def dealias(self, name):
        return next((g.dealias(name) for g in self._groups if g.hasany(name)), super().dealias(name))
    
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
        p = set(parsed) | {next((g.name for g in self._groups if g.hasany(i)), None) for i in parsed} - {None}
        return (
          super().enforce_clumps(p, self._groups)
          and
          all(g.enforce_clumps(parsed) for g in self._groups if g.name in p)
          )
    
    def _extract_flargs(self, inp):
        flags = []
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
                    flags.append((self.dealias(value.lstrip(self.flag_prefix)), inp[idx:skip+idx]))
                continue
            
            for name in filter(self.hasflag, value[1:]):  # short
                skip = self.getflag(name).argcount
                next_pos = next((i for i, v in enumerate(inp[idx:]) if v.startswith(self.flag_prefix)), len(inp))
                if next_pos < skip:
                    skip = next_pos
                flags.append((self.dealias(name), inp[idx:skip+idx]))
        
        return flags, args
    
    def _clear_namespaces(self):
        for entity in chain(self.flags.values(), self.args.values()):
            entity.clear_nsp()
        for entity in (e for g in self._groups for e in chain(g.flags.values(), g.args.values(), g.commands.values())):
            entity.clear_nsp()
    
    def do_parse(self, inp=None, *, flargs=None):
        parsed = {}
        flags, positionals = self._extract_flargs(inp) if flargs is None else flargs
        
        if 'help' in flags or 'h' in flags:
            self.print_help()
            raise SystemExit('\n')
        
        consumed = set()
        for idx, (flag, args) in enumerate(flags):
            if self.hasflag(flag):
                consumed.add(idx)
                entity = self.getflag(flag)
                parsed[flag] = entity(*args)
        flags[:] = [v for i, v in enumerate(flags) if i not in consumed]
        
        consumed.clear()
        for idx, value in enumerate(positionals):
            if self.hascmd(value):
                used, parsed[self._aliases.get(value, value)] = self.getcmd(value).do_parse(
                  flargs=(flags, positionals[1+idx:])
                  )
                consumed.update(map((1 + idx).__add__, used | {-1}))
        positionals[:] = [v for i, v in enumerate(positionals) if i not in consumed]
        used = consumed
        
        consumed.clear()
        for idx, (value, (name, arg)) in enumerate(zip(positionals, self.args.items())):
            consumed.add(idx)
            parsed[name] = arg(value)
        positionals[:] = [v for i, v in enumerate(positionals) if i not in consumed]
        
        self.enforce_clumps(parsed)
        
        final = {**self._defaults, **{name: value for g in self._groups for name, value in g._defaults.items()}, **parsed}
        nsp = ErgoNamespace(**final)
        if self._req_names.difference(nsp):
            raise errors.RequirementError('Expected the following required arguments: {}\nGot {}'.format(
              ", ".join(map(repr, self._req_names)),
              ", ".join(map(repr, self._req_names.intersection(nsp))) or 'none'
              )
            )
        
        if flargs is None:
            return nsp
        return used, nsp
    
    def parse(self, inp, *, systemexit=None):
        try:
            return self.do_parse(inp)
        except Exception as e:
            if systemexit is None and self.systemexit or systemexit:
                self.print_help()
                raise SystemExit(e if str(e) else type(e))
            raise
        finally:
            self._clear_namespaces()
    
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
        return ClumpGroup(self._aliases.get(i, i) for i in chain(self._and, self.parent.parent_and))
    
    @property
    def parent_or(self):
        return ClumpGroup(self._aliases.get(i, i) for i in chain(self._or, self.parent.parent_or))
    
    @property
    def parent_xor(self):
        return ClumpGroup(self._aliases.get(i, i) for i in chain(self._xor, self.parent.parent_xor))


class Group(SubHandler):
    def arg(self, required=False):
        def inner(cb):
            entity = Entity(cb)
            if required:
                self._required.add(entity)
            self.args[entity.name] = entity
            return self.parent.arg(required)(entity.callback)
        return inner


class Subparser(SubHandler, ParserBase):
    def __init__(self, flag_prefix='-', *, parent, name):
        SubHandler.__init__(self, parent, name)
        ParserBase.__init__(self, flag_prefix)
    
    def __str__(self):
        return ' {}'.format(self.name)
    

class Parser(ParserBase):
    def parse(self, inp=sys.argv[1:], **kwargs):
        if isinstance(inp, str):
            inp = shlex.split(inp)
        return super().parse(list(inp), **kwargs)  # inp.copy()
    
    def __str__(self):
        return ''
