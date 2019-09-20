import inspect
from ast import literal_eval
from functools import partial, wraps
from itertools import islice, starmap
from types import SimpleNamespace


_Null = type(
  '_NullType', (),
  {'__bool__': lambda self: False,
   '__repr__': lambda self: '<_Null>'}
  )()
VAR_POSITIONAL, KEYWORD_ONLY = inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.KEYWORD_ONLY


def _callable(obj):
    return callable(obj) and obj is not inspect._empty


def convert(hint, val):
    return hint(val) if _callable(hint) else val


def typecast(func):
    """
    Wraps func such that arguments passed to it will be converted
    according to its typehints.
    
    More specifically, calls func's annotations on arguments
    passed to it; non-callable annotations are not touched.
    If a callable annotates a variadic argument (*, **),
    the annotation will be called on each value therein.
    """
    def _hint_for(param):
        return func.__annotations__.get(param.name)

    params = inspect.signature(func).parameters.values()
    # Gather annotations
    # ...of positional parameters
    pos = [_hint_for(p) for p in params if p.kind < VAR_POSITIONAL]
    var_pos = next((_hint_for(p) for p in params if p.kind == VAR_POSITIONAL), None)
    pos_defaults = [p.default for p in params if p.kind < VAR_POSITIONAL]
    
    # ...of keyword parameters
    kw = {p.name: _hint_for(p) for p in params if p.kind == KEYWORD_ONLY}
    var_kw = next((_hint_for(p) for p in params if p.kind > KEYWORD_ONLY), None)
    kw_defaults = {p.name: p.default for p in params if p.kind == KEYWORD_ONLY}
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_, kwargs_ = [], {}
        # Can use a consumable generator to keep track of what
        # positionals are left to convert
        arg_iter = iter(args)
        if len(args) > len(pos) and not var_pos:
            # More positional arguments were passed than func accepts
            func(*args, **kwargs)  # raise TypeError
        # Type-convert the positional arguments that were passed as such
        args_.extend(starmap(convert, zip(pos, arg_iter)))
        # Fill in the rest with either positional parameters passed as kwargs
        # or, failing that, each parameter's default value
        for param, hint, default in islice(zip(params, pos, pos_defaults), len(args_), None):
            if param.name in kwargs:
                args_.append(convert(hint, kwargs.pop(param.name)))
            else:
                args_.append(default)
        # If some positionals aren't present and also don't have defaults,
        if inspect._empty in args_:
            # Then they were simply not passed as positionals,
            # but they may have been passed via keyword:
            for idx, (param, hint, passed) in enumerate(zip(params, pos, args_)):
                if passed is not inspect._empty:
                    # Only look at those for which nothing was passed
                    continue
                try:
                    args_[idx] = convert(hint, kwargs.pop(param.name))
                except KeyError:
                    # Then this parameter wasn't given, period
                    func(*args, **kwargs)  # raise TypeError
        # If func accepts *args and arg_iter has any values left in it, they
        # should be passed to *args
        if var_pos is not None:
            args_.extend(map(var_pos, arg_iter) if _callable(var_pos) else arg_iter)
        # Keyword-parameter typehints:
        for name, hint in kw.items():
            try:
                kwargs_[name] = convert(hint, kwargs[name])
            except KeyError:
                default = kw_defaults[name]
                if default is inspect._empty:
                    # Keyword argument was not passed and has no default
                    func(*args, **kwargs)  # raise TypeError
                kwargs_[name] = default
        # **kwargs: just convert every value while keeping the dict otherwise intact
        if var_kw is not None:
            kwargs_.update({name: convert(var_kw, val) for name, val in kwargs.items() if name not in kwargs_})
        return func(*args_, **kwargs_)
    return wrapper


def booly(arg):
    """
    arg: str representing something boolean-like
    return: boolean representation of `arg`
    """
    comp = arg.lower()
    if comp in ('yes', 'y', 'true', 't', '1'):
        return True
    elif comp in ('no', 'n', 'false', 'f', '0'):
        return False
    else:
        raise ValueError('Could not convert {!r} to boolean'.format(arg))


class auto:
    """
    Performs literal_eval for whatever it's called on,
    optionally checking types
    """
    def __new__(cls, obj, *rest):
        if isinstance(obj, str) and not rest:
            return cls._leval(obj)
        return super().__new__(cls)
    
    def __init__(self, *types):
        self.types = types
        self.negated = False
        for type_ in self.types:
            if not isinstance(type_, type):
                raise TypeError("auto() argument '{}' is not a type".format(type_))
    
    def __invert__(self):
        """
        Toggle whether to check
          isinstance(..., self.types)
        vs
          not isinstance(...)
        """
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
    def _leval(s):
        """
        s: str to evaluate as literal
        return: literal represented by s (or s itself if none)
        """
        try:
            return literal_eval(s)
        except (SyntaxError, ValueError):
            return s


class multiton:
    """
    Decorator that turns a class into a multiton;
    sameness is determined by class.__init__() arguments.
    """
    classes = {}
    
    def __init__(self, pos=None, *, kw=False, cls=None, hash_by=None):
        """
        pos: where to stop reading positional arguments (i.e. read args[:pos])
        kw: whether to take into account keyword arguments
        cls: class to consider this multiton a part of (i.e. class to instantiate
          when user tries to instantiate the decorated class)
        hash_by: a hash function for when args/kwargs are mutable
        """
        self.class_ = cls
        self.kw = kw
        self.pos = pos
        self.hash_func = hash_by
    
    def __call__(self, deco_cls):
        cls = self.class_ or deco_cls
        instances = self.classes.setdefault(cls, {})
        
        def get_instance(*args, **kwargs):
            key = (args[:self.pos], kwargs) if self.kw else args[:self.pos]
            if self.hash_func is not None:
                key = tuple(map(self.hash_func, key))
            if key not in instances:
                instances[key] = deco_cls(*args, **kwargs)
            return instances[key]
        
        get_instance.cls = deco_cls
        return get_instance


class JoffreyNamespace(SimpleNamespace):
    """
    dict+SimpleNamespace with a `_` attribute
    for additional dict-like stuff
    (needed because, say, JoffreyNamespace().values()
    may conflict with an item named 'values'; a single
    underscore is less likely to conflict with anything
    chosen by a user)
    """
    def __bool__(self):
        return bool(vars(self))
    
    def __eq__(self, other):
        return vars(self) == other
    
    def __contains__(self, name):
        return self._._contains_(name)
    
    def __getitem__(self, name):
        return self._._getitem_(name)
    
    def __getattr__(self, name):
        return self._._getitem_(name)
    
    def __iter__(self):
        yield from vars(self)
    
    @property
    def _(self):
        return _SubNamespace(self)


@multiton(hash_by=id)
class _SubNamespace:
    def __init__(self, parent):
        self._parent = parent
        parent_dict = vars(parent)
        self.items = parent_dict.items
        self.keys = parent_dict.keys
        self.values = parent_dict.values
        self.get = parent_dict.get
        
        # These used to be overridable due to the whole 'default key' thing
        self._getitem_ = parent.__getattribute__
        self._contains_ = parent_dict.__contains__
    
    def pretty(self, delim='\n', sep=': '):
        """
        delim: string to join items with
        sep: what to separate key from value with
        """
        return delim.join(
          '{}{}{}'.format(k, sep, v)
          for k, v in self.items()
          )
