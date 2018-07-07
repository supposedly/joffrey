import inspect
from ast import literal_eval
from functools import wraps
from itertools import starmap
from types import SimpleNamespace


_Null = type(
  '_NullType', (),
  {
    '__bool__': lambda self: False,
    '__repr__': lambda self: '<_Null>',
  }
  )()
VAR_POSITIONAL, KEYWORD_ONLY = inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.KEYWORD_ONLY


def _callable(obj):
    return callable(obj) and obj is not inspect._empty


def convert(hint, val):
    return hint(val) if _callable(hint) else val


def typecast(func):
    def _hint_for(param):
        return func.__annotations__.get(param.name)
    
    params = inspect.signature(func).parameters.values()
    
    pos = [_hint_for(p) for p in params if p.kind < VAR_POSITIONAL]
    var_pos = [_hint_for(p) for p in params if p.kind == VAR_POSITIONAL]
    pos_defaults = [p.default for p in params if p.kind < VAR_POSITIONAL]
    
    kw = {p.name: _hint_for(p) for p in params if p.kind == KEYWORD_ONLY}
    var_kw = [_hint_for(p) for p in params if p.kind > KEYWORD_ONLY]
    kw_defaults = {p.name: p.default for p in params if p.kind == KEYWORD_ONLY}
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_, kwargs_ = [], {}
        arg_iter = iter(args)
        
        if len(args) > len(pos) and not var_pos:
            func(*args, **kwargs)  # Will raise Python TypeError
        
        args_.extend(starmap(convert, zip(pos, arg_iter)))
        args_.extend(pos_defaults[len(args_):])
        if inspect._empty in args_:
            for idx, (param, hint, passed) in enumerate(zip(params, pos, args_)):
                if passed is not inspect._empty:
                    continue
                try:
                    args_[idx] = convert(hint, kwargs.pop(param.name))
                except KeyError:
                    func(*(i for i in args_ if i is not inspect._empty), **kwargs_)  # Will raise Python TypeError
        
        if var_pos:
            hint = var_pos[0]
            args_.extend(map(hint, arg_iter) if _callable(hint) else arg_iter)
        
        for name, hint in kw.items():
            try:
                kwargs_[name] = convert(hint, kw[name])
            except KeyError:
                default = kw_defaults[name]
                if default is inspect._empty:
                    func(*args, **kwargs)  # Will raise Python TypeError
                kwargs_[name] = default
        
        if var_kw:
            hint = var_kw[0]
            kwargs_.update({name: convert(hint, val) for name, val in kwargs if name not in kwargs_})
        
        return func(*args_, **kwargs_)
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
    
    def __init__(self, pos=None, *, kw=False, cls=None):
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
