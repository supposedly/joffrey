from .misc import multiton


class ClumpSet(set):
    """
    Holds a set of clump-checkers (and facilitates checking therewith)
    """
    def successes(self, parsed):
        """
        return: all entity names that are or are not in `parsed` as expected
        """
        return {name for c in self if c.verify(parsed) for name in c.member_names}
    
    def failures(self, parsed):
        """
        return: generator of (expected, the_only_successes) from all clumps that
        `parsed` does not satisfy
        """
        return ((c.member_names, c.to_eliminate(parsed)) for c in self if not c.verify(parsed))


class _Clump:
    def __init__(self, key, host):
        """
        key: Unique string with which to group other ANDs
        host: Handler creating this clump; only used for multiton
          instance-checking
        """
        self.key = key
        self.host = host
        # self.members holds everything this clump checks against
        self.members = set()
    
    @property
    def member_names(self):
        return frozenset(i.name for i in self.members)
    
    def add(self, item):
        self.members.add(item)


@multiton()
class And(_Clump):
    def verify(self, parsed):
        # Should contain either no members or all members (latter indicating none were given)
        diff = self.member_names.difference(parsed)
        return not diff or parsed == diff
    
    def to_eliminate(self, parsed):
        """
        return: entities in `parsed` that were expected to be present.
        (that is, all these methods return successes)
        """
        return frozenset(self.member_names.intersection(parsed))


@multiton()
class Or(_Clump):
    def verify(self, parsed):
        # Should contain at least 1 member
        return bool(self.member_names.intersection(parsed))
    
    def to_eliminate(self, parsed):
        """
        return: entities in `parsed` that were expected to be present.
        """
        return frozenset(self.member_names.intersection(parsed))


@multiton()
class Xor(_Clump):
    def verify(self, parsed):
        # Should contain exactly 1 member
        return len(self.member_names.intersection(parsed)) == 1
    
    def to_eliminate(self, parsed):
        """
        return: entities not in `parsed` that were not expected to be present.
        """
        return frozenset(self.member_names.difference(parsed))
