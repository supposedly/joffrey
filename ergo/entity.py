import inspect
import sys

from .misc import multiton, typecast, _Null

VAR_POS = inspect.Parameter.VAR_POSITIONAL


@multiton(kw=False)
class Entity:
    def __init__(self, func, *, name=None, namespace=None, help=None):
        params = inspect.signature(func).parameters
        has_nsp = bool(namespace)
        self._args = [i.upper() for i in params][has_nsp:]
        self.argcount = sys.maxsize if any(i.kind == VAR_POS for i in params.values()) else len(params) - has_nsp
        self.func, self.callback = func, typecast(func)
        self.help = func.__doc__ or '' if help is None else help
        self.identifier = name or func.__name__
        self.name = self.identifier
        self.namespace = namespace
        self.AND = self.OR = self.XOR = _Null
    
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
        if self._args:
            return ' ' + ' '.join(self._args[:-1]) + ' {}{}'.format(
              '*' if self.argcount == sys.maxsize else '',
              self._args[-1]
              )
        return ''
    
    def __str__(self):
        if self.short is None:
            return '[--{}{}]'.format(self.name, self.args)
        return '[-{} | --{}{}]'.format(self.short, self.name, self.args)


@multiton(cls=Entity.cls, kw=False)
class Arg(Entity.cls):
    def __init__(self, cb, repeat_count, **kwargs):
        super().__init__(cb, **kwargs)
        self.name = self.identifier
        self.repcount = '...' if repeat_count is ... else repeat_count
    
    def __str__(self):
        return '{}({})'.format(self.identifier, self.repcount)
