import inspect
from ast import literal_eval
from functools import wraps
from itertools import zip_longest
from types import SimpleNamespace


def typecast(func):
    params = inspect.signature(func).parameters.values()
    
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
        if len(args) < len(pos_annot):
            raise TypeError("{}() expected at least {} arguments, got {}".format(func.__name__, len(pos_annot), len(args)))
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


def _leval(obj):
    try:
        return literal_eval(obj)
    except (SyntaxError, ValueError):
        return obj


def auto(obj, *rest):
    if isinstance(obj, str):
        return _leval(obj)
    
    types = (obj, *rest)
    if not all(isinstance(i, type) for i in types):
        raise TypeError('auto() argument "{}" is not a type'.format(
          next(i for i in types if not isinstance(i, type))
        ))
    
    def inner(obj):
        ret = _leval(obj)
        if not isinstance(ret, types):
            raise TypeError('Expected {}, got {} {!r}'.format(
              '/'.join(i.__name__ for i in types),
              type(ret).__name__,
              ret
            ))
        return ret
    return inner


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
          pretty=(lambda self, sep='\n', delim=': ': sep.join(
            '{}{}{}'.format(k, delim, v)
            for k, v in self._.items()
            )).__get__(self)
          )
