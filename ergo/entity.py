import inspect
import sys
from copy import deepcopy

from .misc import multiton, typecast


VAR_POS = inspect.Parameter.VAR_POSITIONAL


@multiton()
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
        return deepcopy(self._namespace)
    
    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)


@multiton(cls=Entity.cls)
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


@multiton(cls=Entity.cls)
class Arg(Entity.cls):
    def __init__(self, cb, repeat_count, **kwargs):
        super().__init__(cb, **kwargs)
        self.name = self.identifier
        self.repcount = repeat_count
    
    def __str__(self):
        return '{}({})'.format(self.identifier, '...' if self.repcount is Ellipsis else self.repcount)
