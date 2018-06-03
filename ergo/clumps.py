from .misc import multiton


class _Clump:
    def __init__(self, key, host):
        self.key = key
        self.host = host
        self.members = set()
    
    @property
    def _member_names(self) -> set:
        return {i.name for i in self.members}
    
    def add(self, item):
        self.members.add(item)


@multiton(kw=False)
class And(_Clump):
    def verify(self, parsed) -> set:
        return self._member_names.difference(parsed)


@multiton(kw=False)
class Or(_Clump):
    def verify(self, parsed) -> bool:
        return bool(self._member_names.union(parsed))


@multiton(kw=False)
class Xor(_Clump):
    def verify(self, parsed) -> bool:
        return bool(self._member_names.symmetric_difference(parsed))
