from .misc import multiton


class ClumpGroup(set):
    def successes(self, parsed):
        return {name for c in self if c.verify(parsed) for name in c.member_names}
    
    def failures(self, parsed):
        return ((c.member_names, c.to_eliminate(parsed)) for c in self if not c.verify(parsed))


class _Clump:
    def __init__(self, key, host):
        self.key = key
        self.host = host
        self.members = set()
    
    @property
    def member_names(self):
        return frozenset(i.name for i in self.members)
    
    def add(self, item):
        self.members.add(item)


@multiton()
class And(_Clump):
    def verify(self, parsed):
        # this should contain either no members or all members (latter indicating none were given)
        diff = self.member_names.difference(parsed)
        return not diff or parsed == diff
    
    def to_eliminate(self, parsed):  # received
        return frozenset(self.member_names.intersection(parsed))


@multiton()
class Or(_Clump):
    def verify(self, parsed):
        # this should contain at least 1 member
        return bool(self.member_names.intersection(parsed))
    
    def to_eliminate(self, parsed):  # received
        return frozenset(self.member_names.intersection(parsed))


@multiton()
class Xor(_Clump):
    def verify(self, parsed):
        # this should contain exactly 1 member
        return len(self.member_names.intersection(parsed)) == 1
    
    def to_eliminate(self, parsed):  # not received
        return frozenset(self.member_names.difference(parsed))
