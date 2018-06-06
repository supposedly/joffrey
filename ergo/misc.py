from functools import wraps
from types import SimpleNamespace


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
    
    def __getitem__(self, name):
        return self.__getattribute__(name)
    
    def __iter__(self):
        yield from vars(self)
    
    def items(self):
        return vars(self).items()
    
    def keys(self):
        return vars(self).keys()
    
    def values(self):
        return vars(self).values()
