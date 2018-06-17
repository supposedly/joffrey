"""ergo as a single file"""
import sys
import os
import shlex
import inspect
from ast import literal_eval
from functools import wraps, partial
from itertools import chain, zip_longest
from types import SimpleNamespace
from copy import deepcopy
from keyword import iskeyword


__all__ = 'Parser', 'auto', 'booly', 'errors'

_Null = type(
  '_NullType', (),
  {
    '__bool__': lambda self: False,
    '__repr__': lambda self: '<_Null>',
  }
  )()


def typecast(func):
    params = inspect.signature(func).parameters.values()
    defaults = [p.default for p in params]
    num_expected = sum(d is inspect._empty for d in defaults)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not params:
            return func(*args, **kwargs)
        # Prepare list/dict of all positional/keyword args with annotation or None
        pos_annot, kw_annot = (
          [func.__annotations__[p.name] for p in params if p.kind < 3 and p.name in func.__annotations__],
          {p.name if p.kind == 3 else None: func.__annotations__.get(p.name) for p in params if p.kind >= 3}
          )
        # Assign default to handle **kwargs annotation if not given/callable
        if not callable(kw_annot.get(None)):
            kw_annot[None] = lambda x: x
        if len(args) < num_expected:  # TODO: do this for kwargs as well (although kwargs won't be an ergo thing)
            func(*args)  # will raise Python's error
            # raise TypeError("{}() expected at least {} argument/s, got {}".format(func.__name__, num_expected, len(args)))
        if len(args) < len(pos_annot):
            pos_annot = [i < len(args) and v for i, v in enumerate(pos_annot)]
            args = (*args, *defaults[len(args):])
        # zip_longest to account for any var_positional argument
        fill = zip_longest(pos_annot, args, fillvalue=pos_annot[-1] if pos_annot else None)
        return func(
          *(hint(val) if callable(hint) else val for hint, val in fill),
          **{a: kw_annot[a](b) if a in kw_annot and callable(kw_annot[a]) else kw_annot[None](b) for a, b in kwargs.items()}
          )
    return wrapper


def booly(arg):
    comp = arg.lower()
    if comp in ('yes', 'y', 'true', 't', '1'):
        return True
    elif comp in ('no', 'n', 'false', 'f', '0'):
        return False
    else:
        raise ValueError('Could not convert {!r} to boolean'.format(arg))


class auto:
    def __new__(cls, obj, *rest):
        if isinstance(obj, str) and not rest:
            return cls._leval(obj)
        return super().__new__(cls)
    
    def __init__(self, *types):
        self.types = types
        self.negated = False
        
        if not all(isinstance(i, type) for i in self.types):
            raise TypeError("auto() argument '{}' is not a type".format(
              next(i for i in self.types if not isinstance(i, type))
            ))
    
    def __invert__(self):
        self.negated ^= True
        return self
    
    def __call__(self, obj):
        ret = self._leval(obj)
        if self.negated:
            if isinstance(ret, self.types):
                raise TypeError('Did not expect {}-type {!r}'.format(
                  type(ret).__name__,
                  ret
                ))
        elif not isinstance(ret, self.types):
            raise TypeError('Expected {}, got {} {!r}'.format(
              '/'.join(i.__name__ for i in self.types),
              type(ret).__name__,
              ret
            ))
        return ret
    
    @staticmethod
    def _leval(obj):
        try:
            return literal_eval(obj)
        except (SyntaxError, ValueError):
            return obj


class multiton:
    classes = {}
    
    def __init__(self, pos=None, *, kw, cls=None):
        self.class_ = cls
        self.kw = kw
        self.pos = pos
    
    def __call__(self, deco_cls):
        cls = self.class_ or deco_cls
        if cls not in self.classes:
            self.classes[cls] = {}
        instances = self.classes[cls]
        
        @wraps(deco_cls)
        def getinstance(*args, **kwargs):
            key = (args[:self.pos], kwargs) if self.kw else args[:self.pos]
            if key not in instances:
                instances[key] = deco_cls(*args, **kwargs)
            return instances[key]
        getinstance.cls = deco_cls
        return getinstance


class ErgoNamespace(SimpleNamespace):
    def __bool__(self):
        return bool(vars(self))
    
    def __contains__(self, name):
        return hasattr(self, name)
    
    def __eq__(self, other):
        return vars(self) == other
    
    def __getitem__(self, name):
        return self.__getattribute__(name)
    
    def __iter__(self):
        yield from vars(self)
    
    @property
    def _(self):
        return SimpleNamespace(
          items=vars(self).items,
          keys=vars(self).keys,
          values=vars(self).values,
          pretty=(lambda self, sep='\n', delim=': ':
            sep.join(
              '{}{}{}'.format(k, delim, v)
              for k, v in self._.items()
            )).__get__(self)
          )

class ClumpGroup(set):
    def successes(self, parsed):
        return {name for c in self if c.verify(parsed) for name in c.member_names}
    
    def failures(self, parsed):
        return ((c.member_names, c.to_eliminate(parsed)) for c in self if not c.verify(parsed))


class _Clump:
    def __init__(self, key, host):
        self.key = key
        self.host = host
        self.members = set()
    
    @property
    def member_names(self):
        return frozenset(i.name for i in self.members)
    
    def add(self, item):
        self.members.add(item)


@multiton(kw=False)
class And(_Clump):
    def verify(self, parsed):
        # this should contain either no members or all members (latter indicating none were given)
        r = self.member_names.difference(parsed)
        return not r or parsed == r
    
    def to_eliminate(self, parsed):  # received
        return frozenset(self.member_names.intersection(parsed))


@multiton(kw=False)
class Or(_Clump):
    def verify(self, parsed):
        # this should contain at least 1 member
        return bool(self.member_names.intersection(parsed))
    
    def to_eliminate(self, parsed):  # received
        return frozenset(self.member_names.intersection(parsed))


@multiton(kw=False)
class Xor(_Clump):
    def verify(self, parsed):
        # this should contain exactly 1 member
        return 1 == len(self.member_names.intersection(parsed))
    
    def to_eliminate(self, parsed):  # not received
        return frozenset(self.member_names.difference(parsed))


VAR_POS = inspect.Parameter.VAR_POSITIONAL


@multiton(kw=False)
class Entity:
    def __init__(self, func, *, name=None, namespace=None, help=None):
        params = inspect.signature(func).parameters
        has_nsp = bool(namespace)
        first_optional = next((i for i, v in enumerate(params.values()) if v.default is not inspect._empty), sys.maxsize)
        self._namespace = namespace
        self.params = list(params)[has_nsp:]
        self.argcount = sys.maxsize if any(i.kind == VAR_POS for i in params.values()) else len(params) - has_nsp
        self._normalized_params = [
          ('({})'.format(v) if i >= first_optional else v).upper()
          for i, v in enumerate(self.params[:-1])
          ]
        if self.params:
            s = self.params[-1]
            if self.argcount == sys.maxsize:
                self._normalized_params.append('{}...'.format(s).upper())
            else:
                self._normalized_params.append(('({})'.format(s) if len(params) >= first_optional else s).upper())
        self.func, self.callback = func, typecast(func)
        self.help = inspect.cleandoc(func.__doc__ or '' if help is None else help)
        self.brief = next(iter(self.help.split('\n')), '')
        self.identifier = name or func.__name__
        self.name = self.identifier
    
    @property
    def namespace(self):
        return deepcopy(self._namespace)
    
    @property
    def man(self):
        return '{}\n\n{}'.format(
          self, self.help
          )
    
    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)


@multiton(cls=Entity.cls, kw=False)
class Flag(Entity.cls):
    def __init__(self, *args, _='-', **kwargs):
        super().__init__(*args, **kwargs)
        self.name = self.identifier.replace('_', _)
        self.short = None
    
    @property
    def args(self):
        return ' ' + ' '.join(self._normalized_params) if self.params else ''
    
    def __str__(self):
        if self.short is None:
            return '[--{}{}]'.format(self.name, self.args)
        return '[-{} | --{}{}]'.format(self.short, self.name, self.args)


@multiton(cls=Entity.cls, kw=False)
class Arg(Entity.cls):
    def __init__(self, cb, repeat_count, **kwargs):
        super().__init__(cb, **kwargs)
        self.name = self.identifier
        self.repcount = repeat_count
    
    def __str__(self):
        return '{}({})'.format(self.identifier, '...' if self.repcount is Ellipsis else self.repcount)

class ErgoException(Exception):
    def __init__(self, msg, **kwargs):
        self.details = ErgoNamespace(**kwargs)
        super().__init__(msg)


class ANDError(ErgoException):
    pass


class ORError(ErgoException):
    pass


class XORError(ErgoException):
    pass


class RequirementError(ErgoException):
    pass


_FILE = os.path.basename(sys.argv[0])


class HelperMixin:
    @property
    def all_commands(self):
        return (*self.commands, *(name for g in self._groups for name in g.commands))
    
    @property
    def all_flags(self):
        return (*self.flags.values(), *(entity for g in self._groups for entity in g.flags.values()))
    
    @property
    def all_args(self):
        return map(self.getarg, self.args)
    
    @property
    def usage_info(self):
        return '{}{} {} {}'.format(
          _FILE,
          str(self),
          ' '.join(map(str, self.all_flags)),
          ' '.join(map(str, self.all_args)),
          )
    
    @property
    def help_info(self):
        return '\n'.join(
          '{}\n{}'.format(
            label.upper(),
            '\n'.join({
              '\t{: <15} {}'.format(i.name, i.brief)
              for i in getattr(self, 'all_' + label)
            }),
          )
          for label in ('args', 'flags')
        )
    
    def format_help(self, usage=True, commands=True):
        built = []
        if usage:
            built.append('usage: {}'.format(self.usage_info))
        if commands and self.commands:
            built.append('subcommands: {}'.format(','.join(map(str, self.all_commands))))
        if usage or commands:
            built.append('')
        built.append(self.help_info)
        return '\n' + '\n'.join(built)
    
    def print_help(self, usage=True, commands=True):
        print(self.format_help(usage, commands), end='\n\n')
    
    def error(self, exc=None):
        self.print_help()
        if exc is None:
            raise SystemExit
        raise SystemExit(exc if str(exc) else type(exc))
    
    def help(self, name=None):
        if name is None:
            self.error()
        try:
            print('', self.get(name).man, sep='\n', end='\n\n')
        except AttributeError:
            print('No helpable entity named {!r}'.format(name))
        finally:
            raise SystemExit


class _Handler:
    def __init__(self):
        self.arg_map = {}
        self.commands = {}
        self.flags = {}
        self._aliases = {}
        self._defaults = {}
        
        self.args = []
        self._last_arg_consumes = False
        
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
    def entity_names(self):
        return set(chain(self.arg_map, self.commands, self.flags))
    
    def dealias(self, name):
        return self._aliases.get(name, name)
    
    def remove(self, obj):
        name = obj.identifier if isinstance(obj, Entity.cls) else obj
        if name in self.arg_map:
            del self.arg_map[name]
            self.args = list(filter(name.__eq__, self.args))
        else:
            try:
                del next(filter(lambda c: name in c, (self.commands, self.flags)))[name]
            except StopIteration:
                raise KeyError('No such entity: {}'.format(obj))
        self._aliases = {k: v for k, v in self._aliases.items() if v != name}
    
    def get(self, name):
        for func in (self.getarg, self.getflag, self.getcmd):
            try:
                return func(name)
            except KeyError:
                pass
        return None
    
    def getarg(self, name):
        try:
            return self.arg_map[name]
        except KeyError:
            return self._aliases[self.arg_map[name]]
    
    def getflag(self, name):
        try:
            return self.flags[name]
        except KeyError:
            return self.flags[self._aliases[name]]
    
    def getcmd(self, name):
        try:
            return self.commands[name]
        except KeyError:
            return self.commands[self._aliases[name]]
    
    def hasflag(self, name):
        return name in self.flags or self._aliases.get(name, _Null) in self.flags
    
    def hascmd(self, name):
        return name in self.commands or self._aliases.get(name, _Null) in self.commands
    
    def hasany(self, name):
        return self.hasflag(name) or self.hascmd(name) or name in self.arg_map or self._aliases.get(name, _Null) in self.arg_map
    
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
    
    def enforce_clumps(self, parsed, groups=None):
        elim = {lbl.upper(): getattr(self, 'parent_'+lbl).successes(parsed) for lbl in ('and', 'or', 'xor')}
        if groups is not None:
            g_clumps = {lbl: {groups.get(i) for i in set(successes).intersection(groups)} for lbl, successes in elim.items()}
            zipped = {lbl: (elim[lbl], {name for g in groups for name in g.entity_names}) for lbl, groups in g_clumps.items()}
            elim = {lbl: grp.union(success) for lbl, (success, grp) in zipped.items()}
        
        def extract_names(collection):
            if groups is None:
                return map(repr, collection)
            return (
              '[{}]'.format(
                ', '.join(map(repr, groups[n].entity_names))
                )
              if n in groups
              else repr(n)
              for n in collection
              )
        
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
                raise ANDError(
                  'Expected all of the following flags/arguments: {}\n(Got {})'.format(
                      ', '.join(extract_names(all_failed)),
                      ', '.join(extract_names(received)) or 'none'
                    ),
                  **err_details,
                  failed=all_failed, eliminating=received, not_exempt=not_exempt
                  )
        
        for all_failed, received in self._or.failures(parsed):
            # OR failure == member of an OR clump where none were given
            # an OR failure is okay if it's in a satisfied XOR clump (i.e. exactly one other XOR in its clump was given)
            not_exempt = (all_failed - received) - elim['XOR']
            if not_exempt:
                raise ORError(
                  'Expected at least one of the following flags/arguments: {}\n(Got none)'.format(
                      ', '.join(extract_names(all_failed))
                    ),
                  **err_details,
                  failed=all_failed, eliminating=received, not_exempt=not_exempt
                  )
        
        for all_failed, not_received in self._xor.failures(parsed):
            # XOR failure == member of an XOR clump that was given alongside at least one other
            # an XOR failure is okay if it satisfies an AND clump (i.e. all other ANDs in its clump were given)
            not_exempt = (all_failed - not_received) - elim['AND'] - self._required
            if len(not_exempt) > 1:
                raise XORError(
                  'Expected no more than one of the following flags/arguments: {}\n(Got {})'.format(
                      ', '.join(extract_names(all_failed)),
                      ', '.join(extract_names(all_failed-not_received))
                    ),
                  **err_details,
                  failed=all_failed, eliminating=not_received, not_exempt=not_exempt
                  )
        
        return True
    
    def clump(self, *, AND=_Null, OR=_Null, XOR=_Null):
        def inner(cb):
            entity = Entity(cb.func if isinstance(cb, Entity.cls) else cb)
            self._clump(entity, AND, OR, XOR)
            return entity
        return inner
    
    def arg(self, n=1, *, required=False, namespace=None, help=None):
        """
        n: number of times this arg should be received consecutively; pass ... for infinite
        Expected kwargs: _ (str), help (str)
        """
        def inner(cb):
            repeat_count = n
            entity = Arg(cb, n, namespace=namespace, help=help)
            self.arg_map[entity.name] = entity
            if required:
                self._required.add(entity.name)
            if repeat_count is Ellipsis:
                self._last_arg_consumes = True
                repeat_count = 1
            self.args.extend([entity.name] * repeat_count)
            return entity
        return inner
    
    def flag(self, dest=None, short=_Null, *, default=_Null, required=False, namespace=None, help=None, _='-'):
        def inner(cb):
            entity = Flag(cb, namespace=namespace, name=dest, help=help, _=_)
            if dest is not None:
                self._aliases[cb.__name__] = entity.name
            if short is not None:  # _Null == default; None == none
                try:
                    entity.short = short or next(s for s in entity.name if s.isalnum() and s not in self._aliases)
                except StopIteration:
                    pass
                else:
                    self._aliases[entity.short] = entity.name
            if default is not _Null:
                self._defaults[entity.name] = default
            if required:
                self._required.add(entity.name)
            self.flags[entity.name] = entity
            return entity
        return inner
    
    def command(self, name, *args, AND=_Null, OR=_Null, XOR=_Null, aliases=(), _='-', **kwargs):
        subparser = Subparser(*args, **kwargs, name=name, parent=self)
        visual_name = name.replace('_', _)
        for alias in aliases:
            self._aliases[alias] = visual_name
        self._clump(subparser, AND, OR, XOR)
        self.commands[visual_name] = subparser
        return subparser


class ParserBase(_Handler, HelperMixin):
    def __init__(self, flag_prefix='-', systemexit=True, no_help=False):
        self.flag_prefix = flag_prefix
        self.long_prefix = 2 * flag_prefix
        self.systemexit = systemexit
        self._groups = set()
        super().__init__()
        if not flag_prefix:
            raise ValueError('Flag prefix cannot be empty')
        if not no_help:
            self.flags['help'] = self.flag(
              'help',
              help="Prints help and exits\nIf given valid NAME, displays that entity's help"
              )(lambda name=None: self.help(name))
    
    def dealias(self, name):
        try:
            return next(g.dealias(name) for g in self._groups if g.hasany(name))
        except StopIteration:
            return super().dealias(name)
    
    def remove(self, obj):
        name = obj.name if isinstance(obj, Entity.cls) else obj
        for g in self._groups:
            try:
                return g.remove(name)
            except KeyError:
                pass
        return super().remove(name)
    
    def get(self, name):
        try:
            return next(g.get(name) for g in self._groups if g.hasany(name))
        except StopIteration:
            return super().get(name)
    
    def getarg(self, name):
        try:
            return next(g.getarg(name) for g in self._groups if name in g.arg_map)
        except StopIteration:
            return super().getarg(name)
    
    def getflag(self, name):
        try:
            return next(g.getflag(name) for g in self._groups if g.hasflag(name))
        except StopIteration:
            return super().getflag(name)
    
    def getcmd(self, name):
        try:
            return next(g.getcmd(name) for g in self._groups if g.hascmd(name))
        except StopIteration:
            return super().getcmd(name)
    
    def hasflag(self, name):
        return super().hasflag(name) or any(g.hasflag(name) for g in self._groups)
    
    def hascmd(self, name):
        return super().hascmd(name) or any(g.hascmd(name) for g in self._groups)
    
    def hasany(self, name):
        return super().hasany(name) or self._aliases.get(name, _Null) in self.arg_map
    
    def enforce_clumps(self, parsed):
        p = set(parsed) | {next((g.name for g in self._groups if g.hasany(i)), None) for i in parsed} - {None}
        return (
          super().enforce_clumps(p, {g.name: g for g in self._groups})
          and
          all(g.enforce_clumps(parsed) for g in self._groups if g.name in p)
          )
    
    def _put_nsp(self, namespaces, entity):
        return entity if entity.namespace is None else partial(
          entity,
          namespaces.setdefault(
            entity.name,
            ErgoNamespace(**entity.namespace)
            ),
          )
    
    def _extract_flargs(self, inp, strict=False):
        flags = []
        args = []
        command = None
        skip = 0
        for idx, value in enumerate(inp, 1):
            if skip > 0:
                skip -= 1
                continue
            
            if not value.startswith(self.flag_prefix) or value in (self.flag_prefix, self.long_prefix):
                if self.hascmd(value):
                    command = (value, idx)
                    break
                args.append(value)
                if strict and len(args) > len(self.args):
                    raise TypeError('Too many positional arguments (expected {}, got {})'.format(
                      len(self.args), len(args)
                      ))
                continue
            
            if '=' in value:
                name, arg = value.lstrip(self.flag_prefix).split('=', 1)
                if self.hasflag(name):
                    flags.append((self.dealias(name), [arg] if arg else []))
                elif strict:
                    raise TypeError("Unknown flag `{}'".format(value.split('=')[0]))
                continue
            
            if value.startswith(self.long_prefix):
                if self.hasflag(value.lstrip(self.flag_prefix)):  # long
                    skip = self.getflag(value.lstrip(self.flag_prefix)).argcount
                    next_pos = next((i for i, v in enumerate(inp[idx:]) if v.startswith(self.flag_prefix)), len(inp))
                    if next_pos < skip:
                        skip = next_pos
                    flags.append((self.dealias(value.lstrip(self.flag_prefix)), inp[idx:skip+idx]))
                elif strict:
                    raise TypeError("Unknown flag `{}'".format(value))
                continue
            
            for name in value[1:]:  # short
                if self.hasflag(name):
                    skip = self.getflag(name).argcount
                    next_pos = next((i for i, v in enumerate(inp[idx:]) if v.startswith(self.flag_prefix)), len(inp))
                    if next_pos < skip:
                        skip = next_pos
                    flags.append((self.dealias(name), inp[idx:skip+idx]))
                elif strict:
                    raise TypeError("Unknown flag `{}{}'".format(value[0], name))
        
        if strict and len(args) < sum(e not in self._defaults for e in self.arg_map.values()):
            raise TypeError('Too few positional arguments (expected {}, got {})'.format(
              sum(e not in self._defaults for e in self.arg_map.values()),
              len(args)
              ))
        return flags, args, command
    
    def do_parse(self, inp=None, strict=False):
        parsed = {}
        namespaces = {}
        flags, positionals, command = self._extract_flargs(inp, strict)
        prep = partial(self._put_nsp, namespaces)
        
        for flag, args in flags:
            if self.hasflag(flag):
                entity = self.getflag(flag)
                parsed[entity.identifier] = prep(entity)(*args)
        
        if command is not None:
            value, idx = command
            parsed[self._aliases.get(value, value)] = self.getcmd(value).do_parse(inp[idx:], strict)
        
        if self._last_arg_consumes and len(positionals) > len(self.args):
            zipped_args = zip_longest(map(self.getarg, self.args), positionals, fillvalue=self.getarg(self.args[-1]))
        else:
            zipped_args = zip(map(self.getarg, self.args), positionals)
        
        for entity, value in zipped_args:
            parsed[entity.identifier] = prep(entity)(value)
        
        self.enforce_clumps(parsed)
        
        final = {**self._defaults, **{name: value for g in self._groups for name, value in g._defaults.items()}, **parsed}
        nsp = ErgoNamespace(**final)
        
        if self._required.difference(nsp):
            raise RequirementError('Expected the following required arguments: {}\nGot {}'.format(
              ", ".join(map(repr, self._required)),
              ", ".join(map(repr, self._required.intersection(nsp))) or 'none'
              )
            )
        return nsp
    
    def parse(self, inp, *, systemexit=None, strict=False):
        try:
            return self.do_parse(inp, strict)
        except Exception as e:
            if systemexit is None and self.systemexit or systemexit:
                self.error(e)
            raise
    
    def group(self, name, *, required=False, AND=_Null, OR=_Null, XOR=_Null):
        if name in vars(self):
            raise ValueError('Group name already in use for this parser: ' + name)
        if iskeyword(name) or not name.isidentifier():
            raise ValueError('Invalid group name: ' + name)
        group = Group(self, name)
        if required:
            self._required.add(group.name)
        self._clump(group, AND, OR, XOR)
        setattr(self, name, group)
        self._groups.add(group)
        return group


class SubHandler(_Handler):
    def __init__(self, parent, name):
        self.name = name
        self.parent = parent
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
    def arg(self, n=1, **kwargs):
        """
        n: number of times this arg should be received consecutively; pass ... for infinite
        Expected kwargs: _ (str), help (str)
        """
        def inner(cb):
            entity = Arg(cb, n, namespace=kwargs.get('namespace'), help=kwargs.get('help'))
            self.arg_map[entity.name] = entity
            if kwargs.get('required'):
                self._required.add(entity.name)
            return self.parent.arg(n, **kwargs)(entity.func)
        return inner
    
    def flag(self, dest=None, short=_Null, **kwargs):
        def inner(cb):
            entity = Flag(cb, namespace=kwargs.get('namespace'), name=dest, help=kwargs.get('help'), _=kwargs.get('_', '-'))
            if dest is not None:
                self._aliases[cb.__name__] = entity.name
            if short is not None:  # _Null == default; None == none
                try:
                    entity.short = short or next(s for s in entity.name if s.isalnum() and s not in self._aliases)
                except StopIteration:
                    pass
                else:
                    self._aliases[entity.short] = entity.name
            if kwargs.get('default', _Null) is not _Null:  # could be `in` but we don't want them using _Null
                self._defaults[entity.name] = kwargs['default']
            if kwargs.get('required'):
                self._required.add(entity.name)
            self.flags[entity.name] = entity
            return self.parent.flag(dest, short, **kwargs)(entity.func)
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


errors = SimpleNamespace(ANDError=ANDError, ORError=ORError, XORError=XORError, RequirementError=RequirementError)
