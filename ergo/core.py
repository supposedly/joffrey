"""
argparse sucks

this sucks too but less
"""
import inspect
import keyword
import shlex
import sys
from collections import defaultdict
from functools import wraps
from itertools import zip_longest as zipln


_Null = type('_NullType', (), {'__slots__': ()})()


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
        fill = zipln(pos_annot, args, fillvalue=pos_annot[-1] if pos_annot else None)
        return func(
          *(hint(val) if callable(hint) else val for hint, val in fill),
          **{a: kw_annot[a](b) if a in kw_annot and callable(kw_annot[a]) else kw_annot[None](b) for a, b in kwargs.items()}
          )
    return wrapper


class FlagLocalNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)


class Flarg:
    """Flag/argument, do something to resolve aliases"""
    pass


class Parser:
    def __init__(self, *, flag_prefix='-'):
        self._flag_prefix = flag_prefix
        self._long_prefix = 2 * flag_prefix
        self.p_used = True
        self.p_or = self.p_xor = self.p_and = _Null
        if not flag_prefix:
            raise ValueError('Flag prefix must not be empty')
        self._or = defaultdict(lambda: [_Null])
        self._xor = defaultdict(lambda: [_Null])
        self._and = defaultdict(lambda: [_Null])
        self._required = set()
        self._got = set()
        self._groups = set()
        self._final = None
        self._defaults = {}
        self.commands = {}
        self.flags = {}
        self.args = {}
    
    @staticmethod
    def _prep(cb):
        def wrapper(*args, **kwargs):
            if getattr(cb, 'p_namespace', False):
                args = (cb.p_namespace, *args)
            return typecast(cb)(*args, **kwargs)
        return wrapper
    
    def help(self):
        print('FLAGS')
        for name, doc in {i.__name__: i.__doc__ for i in self.flags.values()}.items():
            print(' ', name, ' ' * (15 - len(name)), doc)
        print('ARGS')
        for name, doc in {i.__name__: i.__doc__ for i in self.args.values()}.items():
            print(' ', name, ' ' * (15 - len(name)), doc)

    def parse(self, _inp=sys.argv[1:], *, consume=False):
        args = []
        flags = {}
        final = self._defaults
        skip = 0

        if isinstance(_inp, str):
            _inp = shlex.split(_inp)
        
        if f'{self._long_prefix}help' in _inp or any('h' in i for i in _inp if i.startswith(self._flag_prefix) and not i.startswith(self._long_prefix)):
            self.help()
            sys.exit()
        
        inp = _inp.copy()
        
        for idx, val in enumerate(inp):
            if skip:
                skip -= 1
                continue
            if val.startswith(self._long_prefix):
                flag = val.lstrip(self._flag_prefix)
                skip = self.flags[flag].p_nargs
                next_flag = next(i for i, v in enumerate(inp[idx:], idx) if v.startswith(self._flag_prefix))
                if next_flag < skip + idx:
                    skip -= next_flag - idx
                flags[flag] = self._prep(self.flags[flag])(*inp[1+idx:1+skip+idx])
            elif val.startswith(self._flag_prefix):
                for v in val.lstrip(self._flag_prefix)[:-1]:
                    flags[v] = self._prep(self.flags[v])()
                fin = val[-1]
                skip = self.flags[fin].p_nargs
                next_flag = next(i for i, v in enumerate(inp[idx:], idx) if v.startswith(self._flag_prefix))
                if next_flag < skip + idx:
                    skip -= next_flag - idx
                flags[fin] = self._prep(self.flags[fin])(*inp[1+idx:1+skip+idx])
            else:
                args.append(val)
        
        for arg_idx, (arg, val) in enumerate(zip(self.args, args)):
            if val in self.commands:
                args.pop(arg_idx)
                obj = self.commands[val]
                if not hasattr(obj, 'p_group'):
                    self._resolve_clumps(obj)
                else:
                    obj.p_group._resolve_clumps(obj)
                    if not obj.p_group.p_used:
                        self._resolve_clumps(obj.p_group)
                final[val] = obj.parse(inp[1+inp.index(val):], consume=True)
                continue
            try:
                obj = self.args[arg]
            except KeyError:
                if not consume:
                    raise
                continue
            final[arg] = self._prep(obj)(val)
            if not hasattr(obj, 'p_group'):
                self._resolve_clumps(obj)
            else:
                obj.p_group._resolve_clumps(obj)
                if not obj.p_group.p_used:
                    self._resolve_clumps(obj.p_group)
        
        for flag, res in flags.items():
            final[flag] = res
            obj = self.flags[flag]
            if not hasattr(obj, 'p_group'):
                self._resolve_clumps(obj)
            else:
                obj.p_group._resolve_clumps(obj)
                if not obj.p_group.p_used:
                    self._resolve_clumps(obj.p_group)
        
        self._final = final
        self._check_clumps(final)
        
        for group in self._groups:
            group._check_clumps(final)
        
        if consume:
            # doesn't work (i.e. doesn't do what it's supposed to bc doesn't mutate original list at all)
            for idx in (idx for idx, val in enumerate(_inp) if val in final.values()):
                del _inp[idx]
        return final

    def _resolve_clumps(self, obj):
        obj.p_used = True
        OR = obj.p_or
        AND = obj.p_and
        XOR = obj.p_xor
        if OR is not _Null:
            self._or[OR][0] = True  # one or more (doesn't matter how many)
        if AND is not _Null:
            to_check = [] if self._and[AND][0] is _Null else self._and[AND][0]
            self._and[AND][0] = [i for i in self._and[AND] if _Null is not i is not obj and i not in to_check]  # that should be [] when finished
        if XOR is not _Null:
            self._xor[XOR][0] = self._xor[XOR][0] is _Null  # only once
        if obj in self._required:
            self._got.add(obj)
    
    def _check_clumps(self, final):
        fin_set = set(final)
        
        try:
            # OR
            names = {i.__name__ for i in next(rest for sign, *rest in self._or.values() if not sign and not all(self._xor[j.p_xor] or not j.p_required for j in rest))}
        except StopIteration:
            pass
        else:
            raise ValueError(f'''Expected at least one of the following flags/arguments: '{"', '".join(names)}' (got none)''')
        
        try:
            # XOR
            names = {i.__name__ for i in next(rest for sign, *rest in self._xor.values() if not sign and all(j.p_used if j.p_required else True for j in rest))}
        except StopIteration:
            pass
        else:
            raise ValueError(f'''Expected no more than one of the following flags/arguments: '{"', '".join(names)}' (got '{"', '".join(fin_set & names)}')''')
        
        try:
            # AND
            names = {i.__name__ for i in next(rest for sign, *rest in self._and.values() if sign and getattr(self, 'p_used', True))}
        except StopIteration:
            pass
        else:
            raise ValueError(f'''Expected all of the following flags/arguments: '{"', '".join(names)}' (only got '{"', '".join(fin_set & names)}')''')
        
        if self.p_used and self._required ^ self._got:
            # required
            got = {i.__name__ for i in self._got}
            required = {i.__name__ for i in self._required}
            raise ValueError(f'''Expected the following required flags/arguments: '{"', '".join(required)}' (only got '{"', '".join(fin_set & got)}')''')
    
    def clump(self, *, OR=_Null, XOR=_Null, AND=_Null):
        def wrapper(cb):
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
            return cb
        return wrapper
    
    def command(self, name, *args, aliases=(), OR=_Null, XOR=_Null, AND=_Null, **kwargs):
        ret = self.__class__(*args, **kwargs)
        ret.__name__ = name
        ret.p_used = False
        for name in [ret.__name__, *aliases]:
            self.commands[name] = ret
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
            cb.p_short = short or cb.__name__
            cb.p_namespace = namespace and FlagLocalNamespace(**namespace)
            cb.p_nargs = len(sig.parameters) - bool(namespace)
            cb.p_used = False
            cb.p_required = required
            cb.p_or = cb.p_and = cb.p_xor = _Null
            self.flags[cb.__name__] = self.flags[cb.p_short] = cb
            if default is not _Null:
                self._defaults[cb.__name__] = default
            if required:
                self._required.add(cb)
            return cb
        return wrapper
    
    def group(self, name, *, required=False, OR=_Null, XOR=_Null, AND=_Null):
        if name in vars(self):
            raise ValueError(f'Group name already in use for this parser: {name}')
        if keyword.iskeyword(name) or not name.isidentifier():
            raise ValueError(f'Invalid group name: {name}')
        ret = Group(getattr(self, 'parser', self), name, OR, XOR, AND)
        if required:
            self._required.add(ret)
        if OR is not _Null:
            self._or[OR].append(ret)
        if XOR is not _Null:
            self._xor[XOR].append(ret)
        if AND is not _Null:
            self._and[AND].append(ret)
        setattr(self, ret.__name__, ret)
        self._groups.add(ret)
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
        self._or = defaultdict(lambda: [_Null])
        self._xor = defaultdict(lambda: [_Null])
        self._and = defaultdict(lambda: [_Null])
    
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
    
    def parse(self, *_):
        raise NotImplementedError('Groups cannot parse')
    
    def command(self, *args, **kwargs):
        def wrapper(cb):
            cb.p_group = self
            if kwargs.get('required'):
                self._required.add(cb)
                kwargs['required'] = False
            return self.parser.command(*args, **kwargs)(cb)
        return wrapper
    
    def flag(self, *args, **kwargs):
        def wrapper(cb):
            cb.p_group = self
            if kwargs.get('required'):
                self._required.add(cb)
                kwargs['required'] = False
            return self.parser.flag(*args, **kwargs)(cb)
        return wrapper
    
    def arg(self, *args, **kwargs):
        def wrapper(cb):
            cb.p_group = self
            if kwargs.get('required'):
                self._required.add(cb)
                kwargs['required'] = False
            return self.parser.arg(*args, **kwargs)(cb)
        return wrapper
