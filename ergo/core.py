"""
argparse sucks
this sucks too but less
"""
import inspect
import keyword
import os
import shlex
import sys
from collections import defaultdict
from functools import wraps
from itertools import chain, islice, zip_longest
from types import SimpleNamespace


_FILE = os.path.basename(sys.argv[0])
_Null = type('_NullType', (), {'__slots__': (), '__repr__': lambda self: '<_Null>'})()


def typecast(func):
    params = inspect.signature(func).parameters.items()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not params:
            return func(*args, **kwargs)
        # Prepare list/dict of all positional/keyword args with annotation or None
        pos_annot, kw_annot = (
          [func.__annotations__[p.name] for _, p in params if p.kind < 3 and p.name in func.__annotations__],
          {p.name if p.kind == 3 else None: func.__annotations__.get(p.name) for _, p in params if p.kind >= 3}
          )
        # Assign default to handle **kwargs annotation if not given/callable
        if not callable(kw_annot.get(None)):
            kw_annot[None] = lambda x: x
        # zip_longest to account for any var_positional argument
        fill = zip_longest(pos_annot, args, fillvalue=pos_annot[-1] if pos_annot else None)
        return func(
          *(hint(val) if callable(hint) else val for hint, val in fill),
          **{a: kw_annot[a](b) if a in kw_annot and callable(kw_annot[a]) else kw_annot[None](b) for a, b in kwargs.items()}
          )
    return wrapper


def clump_factory():
    return [_Null]


class FlagLocalNamespace(SimpleNamespace):
    pass


class ErgoNamespace(SimpleNamespace):
    def __getitem__(self, name):
        return self.__getattribute__(name)


class Parser:
    def __init__(self, *, flag_prefix='-'):
        self._flag_prefix = flag_prefix
        self._long_prefix = 2 * flag_prefix
        self.p_used = True
        self.p_required = False
        self.p_or = self.p_xor = self.p_and = _Null
        if not flag_prefix:
            raise ValueError('Flag prefix must not be empty')
        self._or = defaultdict(clump_factory)
        self._xor = defaultdict(clump_factory)
        self._and = defaultdict(clump_factory)
        self._required = set()
        self._got = set()
        self._groups = set()
        self._final = None
        self._defaults = {}
        self._aliases = {}
        self.commands = {}
        self.flags = {}
        self.args = {}
    
    def __repr__(self):
        return '<{!r} {}.{}, flag_prefix={!r}>'.format(
          getattr(self, '__name__', '__main__'),
          self.__class__.__module__,
          self.__class__.__name__,
          self._flag_prefix
          )

    @staticmethod
    def _prep(cb):
        def wrapper(*args, **kwargs):
            if getattr(cb, 'p_namespace', False):
                args = (cb.p_namespace, *args)
            return typecast(cb)(*args, **kwargs)
        return wrapper
    
    @property
    def usage(self):
        flags = {
          ('-{} |'.format(i.p_short) if i.p_short else '', '--{}'.format(i.__name__)):
          ' '.join(i.p_args)
          for i in self.flags.values()
          }
        return '{} {}{} {}'.format(
          _FILE,
          self.__name__ + ' ' if hasattr(self, '__name__') else '',  # for subcommands
          ' '.join(map("`{}'".format, self.args)),
          ' '.join('[{}{}{}]'.format(' '.join(name), ' ' if args else '', args) for name, args in flags.items())
          )
    
    @property
    def help(self):
        return '\n'.join(
          '{}\n{}'.format(
            label.upper(),
            '\n'.join({
              '\t{: <15} {}'.format(i.__name__, i.__doc__)
              for i in getattr(self, label).values()
            }),
          )
          for label in ('args', 'flags')
        )
    
    @property
    def subcommands(self):
        return ', '.join(self.commands)
    
    def format_help(self, usage=True, commands=True):
        built = ['']
        if usage:
            built.append('usage: {}'.format(self.usage))
        if commands and self.commands:
            built.append('subcommands: {}'.format(self.subcommands))
        if usage or commands:
            built.append('')
        built.append(self.help)
        return '\n'.join(built)

    def print_help(self, usage=True):
        print(self.format_help(usage), end='\n\n')
    
    def _parse(self, _inp=sys.argv[1:], *, as_dict=False, consume=False, parent_flags: set = None):
        args = []
        flags = {}
        final = self._defaults
        subcommand_flags = {flag for sub in self.commands.values() for flag in chain(sub.flags, sub._aliases)}
        super_flags = set() if parent_flags is None else parent_flags
        ignored_flags = {*subcommand_flags, *super_flags}
        consumed = set()
        skip = 0

        if isinstance(_inp, str):
            _inp = shlex.split(_inp)
        
        if self._long_prefix + 'help' in _inp or any('h' in i for i in _inp if i.startswith(self._flag_prefix) and not i.startswith(self._long_prefix)):
            raise SystemExit(self.format_help())
        
        inp = _inp.copy()
        
        for idx, val in enumerate(inp):
            if skip:
                skip -= 1
                continue
            if val.startswith(self._long_prefix):
                flag = val.lstrip(self._flag_prefix)
                if flag in ignored_flags:
                    continue
                if consume:
                    consumed.add(idx)
                name = self._aliases.get(flag, flag)
                skip = self.flags[name].p_nargs
                next_pos = next((i for i, v in enumerate(inp[1+idx:]) if v.startswith(self._flag_prefix)), len(inp))
                if next_pos < skip + idx:
                    skip = next_pos
                flags[name] = self._prep(self.flags[name])(*inp[1+idx:1+skip+idx])
            elif val.startswith(self._flag_prefix):
                for v in val.lstrip(self._flag_prefix)[:-1]:
                    if v in ignored_flags:
                        continue
                    if consume:
                        consumed.add(idx)
                    name = self._aliases.get(v, v)
                    flags[name] = self._prep(self.flags[name])()
                fin = self._aliases.get(val[-1], val[-1])
                if fin in ignored_flags:
                    continue
                skip = self.flags[fin].p_nargs
                next_pos = next((i for i, v in enumerate(inp[1+idx:]) if v.startswith(self._flag_prefix)), len(inp))
                if next_pos < skip + idx:
                    skip = next_pos
                flags[fin] = self._prep(self.flags[fin])(*inp[1+idx:1+skip+idx])
                if consume:
                    consumed.update(range(idx, 1 + skip + idx))  # we consumed the flag + all its arguments
            else:
                args.append(val)
                if consume:
                    consumed.add(idx)
        
        for arg_idx, (arg, val) in enumerate(zip(self.args, args)):
            val = self._aliases.get(val, val)
            if val in self.commands:
                args.pop(arg_idx)
                obj = self.commands[val]
                if obj.p_group is not None:
                    obj.p_group._resolve_clumps(obj)
                    if not obj.p_group.p_used:
                        self._resolve_clumps(obj.p_group)
                else:
                    self._resolve_clumps(obj)
                subparse_start = 1 + inp.index(val)
                parsed, _consumed = obj._parse(
                  inp[subparse_start:],
                  consume=True,
                  parent_flags={*super_flags, *self.flags, *self._aliases}
                  )
                final[val] = parsed if as_dict else ErgoNamespace(**parsed)
                _consumed_vals = {inp[i] for i in _consumed}
                for i, v in enumerate(args):  # don't really like this
                    if v in _consumed_vals:
                        del args[i]
                inp = [v for i, v in enumerate(inp, -subparse_start) if i not in _consumed and v != val]
                continue
            
            obj = self.args[arg]
            final[arg] = self._prep(obj)(val)
            if obj.p_group is not None:
                obj.p_group._resolve_clumps(obj)
                if not obj.p_group.p_used:
                    self._resolve_clumps(obj.p_group)
            else:
                self._resolve_clumps(obj)
        
        for flag, res in flags.items():
            final[flag] = res
            obj = self.flags[flag]
            if obj.p_group is not None:
                obj.p_group._resolve_clumps(obj)
                if not obj.p_group.p_used:
                    self._resolve_clumps(obj.p_group)
            else:
                self._resolve_clumps(obj)
        
        self._final = final
        self._check_clumps(final)
        
        for group in self._groups:
            group._check_clumps(final)
        return (final, consumed) if consume else final
    
    def parse(self, *args, as_dict=False, **kwargs):
        try:
            parsed = self._parse(*args, as_dict=as_dict, **kwargs)
        except KeyError as e:
            self.print_help()
            raise SystemExit('Unexpected flag/argument: {}'.format(str(e).split("'")[1]))
        except Exception as e:
            self.print_help()
            raise SystemExit(e if str(e) else type(e))
        return parsed if as_dict else ErgoNamespace(**parsed)
    
    def _resolve_clumps(self, obj):
        obj.p_used = True
        OR = obj.p_or
        AND = obj.p_and
        XOR = obj.p_xor
        if OR is not _Null:
            self._or[OR][0] = True  # one or more (doesn't matter how many)
        if AND is not _Null:
            # self._and[AND][0] will be identical to self._and[AND][1:] when finished
            to_check = [] if self._and[AND][0] is _Null else self._and[AND][0]
            self._and[AND][0] = to_check + [f for f in self._and[AND][1:] if _Null is not f is not obj and f not in to_check]
        if XOR is not _Null:
            self._xor[XOR][0] = self._xor[XOR][0] is _Null  # only once
        if obj in self._required:
            self._got.add(obj)
    
    def _check_clumps(self, final):
        fin_set = set(final)
        fin_names = {self._aliases.get(name, name) for name in fin_set}
        
        try:
            # OR
            or_names = {
              name for i in next(rest for sign, *rest in self._or.values()
                if not sign
                and not all(self._xor[j.p_xor] or not j.p_required for j in rest)
                )
              for name in getattr(i, 'g_name', [i.__name__])
              }
        except StopIteration:
            pass
        else:
            raise ValueError("Expected at least one of the following flags/arguments: '{}' (got none)".format("', '".join(or_names)))
        
        try:
            # XOR
            xor_names = {
              name for i in next(rest for sign, *rest in self._xor.values()
                if not sign
                and all(j.p_used if j.p_required else True for j in rest)
                )
              for name in getattr(i, 'g_name', [i.__name__])
              }
        except StopIteration:
            pass
        else:
            xor_true_names = {self._aliases.get(name, name) for name in xor_names}
            raise ValueError("Expected no more than one of the following flags/arguments: '{}' (got '{}')".format("', '".join(xor_names), "', '".join(fin_names & xor_true_names)))
        
        try:
            # AND
            and_names = {
              name for i in next(rest for sign, *rest in self._and.values()
                if len(
                  [i for i in rest if i.p_xor is not _Null or getattr(i.p_group, 'p_xor', _Null) is not _Null]
                  if sign is _Null else sign
                  ) < len(rest)
                and getattr(self, 'p_used', True)
                )
              for name in getattr(i, 'g_name', [i.__name__])
              }
        except StopIteration:
            pass
        else:
            and_true_names = {self._aliases.get(name, name) for name in and_names}
            raise ValueError("Expected all of the following flags/arguments: '{}' (only got '{}')".format("', '".join(and_names), "', '".join(fin_names & and_true_names)))
        
        if self.p_used and self._required - self._got:
            # required
            got = {self._aliases.get(name, name) for i in self._got for name in getattr(i, 'g_name', [i.__name__])}
            required = {name for i in self._required for name in getattr(i, 'g_name', [i.__name__])}
            raise ValueError("Expected the following required flags/arguments: '{}' (only got '{}')".format("', '".join(required), "', '".join(fin_names & got)))
    
    def clump(self, *, OR=_Null, XOR=_Null, AND=_Null):
        def wrapper(cb):
            if isinstance(self, Group):
                cb.p_group = self  # eeeeh...
            if OR is not _Null:
                self._or[OR].append(cb)
            if XOR is not _Null:
                self._xor[XOR].append(cb)
            if AND is not _Null:
                self._and[AND].append(cb)
            cb.p_or = OR
            cb.p_xor = XOR
            cb.p_and = AND
            return cb
        return wrapper
    
    def arg(self, required=False):
        def wrapper(cb):
            cb.p_required = required
            cb.p_used = False
            cb.p_or = cb.p_and = cb.p_xor = _Null
            self.args[cb.__name__] = cb
            if required:
                self._required.add(cb)
            cb.p_group = getattr(cb, 'p_group', None)
            return cb
        return wrapper
    
    def command(self, name, *args, aliases=(), OR=_Null, XOR=_Null, AND=_Null, **kwargs):
        ret = self.__class__(*args, **kwargs)
        ret.__name__ = name
        ret.p_used = False
        ret.p_group = getattr(ret, 'p_group', None)
        self.commands[name] = ret
        for alias in aliases:
            self._aliases[alias] = name
        if OR is not _Null:
            self._or[OR].append(ret)
        if XOR is not _Null:
            self._xor[XOR].append(ret)
        if AND is not _Null:
            self._and[AND].append(ret)
        return ret
    
    def flag(self, dest=None, short=None, *, default=_Null, namespace={}, required=False):
        def wrapper(cb):
            sig: inspect.Signature = inspect.signature(cb)
            if dest:
                self._aliases[cb.__name__] = dest
            name = dest or cb.__name__
            _short = short if isinstance(short, str) else name[0]
            cb.p_short = _short if _short and _short not in self.flags else None
            cb.p_namespace = namespace and FlagLocalNamespace(**namespace)
            cb.p_args = ['*'[val.kind != 2:] + name.upper() for name, val in islice(sig.parameters.items(), bool(namespace), None)]
            cb.p_nargs = len(sig.parameters) - bool(namespace)
            cb.p_group = getattr(cb, 'p_group', None)
            if any(i.kind == 2 for i in sig.parameters.values()):  # inspect.Parameter.VAR_POSITIONAL == 2
                cb.p_nargs = sys.maxsize  # why not?
            cb.p_used = False
            cb.p_required = required
            cb.p_or = cb.p_and = cb.p_xor = _Null
            self.flags[name] = cb
            if default is not _Null:
                self._defaults[name] = default
            if cb.p_short is not None:
                self._aliases[cb.p_short] = name
            if required:
                self._required.add(cb)
            return cb
        return wrapper
    
    def group(self, name, *, required=False, OR=_Null, XOR=_Null, AND=_Null):
        if name in vars(self):
            raise ValueError('Group name already in use for this parser: ' + name)
        if keyword.iskeyword(name) or not name.isidentifier():
            raise ValueError('Invalid group name: ' + name)
        ret = Group(getattr(self, 'parser', self), name, OR, XOR, AND)
        setattr(self, ret.__name__, ret)
        self._groups.add(ret)
        if required:
            self._required.add(ret)
        if OR is not _Null:
            self._or[OR].append(ret)
        if XOR is not _Null:
            self._xor[XOR].append(ret)
        if AND is not _Null:
            self._and[AND].append(ret)
        return ret


class Group(Parser):
    def __init__(self, parser, name, OR, XOR, AND):
        self.parser = parser
        self.__name__ = name
        self.p_or = OR
        self.p_xor = XOR
        self.p_and = AND
        self.p_used = False
        self.p_required = True
        self._required = set()
        self._got = set()
        self._all = set()
        self._or = defaultdict(clump_factory)
        self._xor = defaultdict(clump_factory)
        self._and = defaultdict(clump_factory)
    
    def __repr__(self):
        return '{}(parser={!r}, name={!r}, OR={!r}, XOR={!r}, AND={!r})'.format(
          self.__class__.__name__,
          self.parser,
          self.__name__,
          self.p_or,
          self.p_xor,
          self.p_and
          )
    
    @property
    def g_name(self):
        return {i.__name__ for i in self._all}
    
    @property
    def args(self):
        return self.parser.args
    
    @property
    def commands(self):
        return self.parser.commands
    
    @property
    def flags(self):
        return self.parser.flags
    
    @property
    def _final(self):
        return self.parser._final
    
    @property
    def _groups(self):
        return self.parser._groups
    
    @property
    def _aliases(self):
        return self.parser._aliases
    
    def parse(self, *_):
        raise NotImplementedError('Groups cannot parse')
    
    def command(self, *args, **kwargs):
        def wrapper(cb):
            cb.p_group = self
            self._all.add(cb)
            if kwargs.get('required'):
                self._required.add(cb)
                kwargs['required'] = False
            return self.parser.command(*args, **kwargs)(cb)
        return wrapper
    
    def flag(self, *args, **kwargs):
        def wrapper(cb):
            cb.p_group = self
            self._all.add(cb)
            if kwargs.get('required'):
                self._required.add(cb)
                kwargs['required'] = False
            return self.parser.flag(*args, **kwargs)(cb)
        return wrapper
    
    def arg(self, *args, **kwargs):
        def wrapper(cb):
            cb.p_group = self
            self._all.add(cb)
            if kwargs.get('required'):
                self._required.add(cb)
                kwargs['required'] = False
            return self.parser.arg(*args, **kwargs)(cb)
        return wrapper
