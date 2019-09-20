import inspect
import sys
from copy import deepcopy

from .misc import multiton, typecast


VAR_POS = inspect.Parameter.VAR_POSITIONAL


@multiton()
class Entity:
    """
    Base class for flags/positional arguments.

    ###  instance attrs  ###
    _namespace: dict containing namespace-initialization values
    _normalized_params: names of arguments this entity takes, formatted prettily
    params: arguments this entity takes
    argcount: how many args this entity can take
    func: original function passed to __init__()
    callback: func decorated with joffrey.misc.typecast()
    help: entity's helptext
    identifier: custom name if __init__() was given one else func.__name__
    name: identical to identifier but subclasses can override
    """
    def __init__(self, func, *, name=None, namespace=None, help=None):
        """
        func: function this entity is to call
        name: entity's name or func.__name__
        namespace: dict with which to initialize a namespace if applicable
        help: entity's help text or func.__doc__
        """
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
            last = self.params[-1]
            if self.argcount == sys.maxsize:
                self._normalized_params.append('{}...'.format(last).upper())
            else:
                self._normalized_params.append(('({})'.format(last) if len(params) >= first_optional else last).upper())
        self.func, self.callback = func, typecast(func)
        self.help = inspect.cleandoc(func.__doc__ or '' if help is None else help)
        self.brief = next(iter(self.help.split('\n')), '')
        self.identifier = name or func.__name__
        self.name = self.identifier
    
    @property
    def namespace(self):
        # must deepcopy because users can modify the returned dict
        return deepcopy(self._namespace)
    
    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)


@multiton(cls=Entity.cls)
class Flag(Entity.cls):
    """
    A flag AKA option (the kind passed in unix with - and --)
    name: identifier but with its underscores replaced by whatever given to __init__()
    short: short alias
    """
    def __init__(self, *args, _='-', **kwargs):
        """
        _: What to replace underscores with in self.name
        """
        super().__init__(*args, **kwargs)
        self.name = self.identifier.replace('_', _)
        self.short = None  # can be reassigned
    
    @property
    def args(self):
        return ' ' + ' '.join(self._normalized_params) if self.params else ''
    
    def __str__(self):
        if self.short is None:
            return '[--{}{}]'.format(self.name, self.args)
        return '[-{} | --{}{}]'.format(self.short, self.name, self.args)


@multiton(cls=Entity.cls)
class Arg(Entity.cls):
    """
    A positional argument
    name: self.identifier
    repcount: how many times this argument is to be consecutively invoked
    """
    def __init__(self, cb, repeat_count, **kwargs):
        super().__init__(cb, **kwargs)
        self.name = self.identifier
        self.repcount = repeat_count
    
    def __str__(self):
        return '{}({})'.format(self.identifier, '...' if self.repcount is Ellipsis else self.repcount)
