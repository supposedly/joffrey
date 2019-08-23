from .misc import KizbraNamespace


class KizbraException(Exception):
    """
    Base class for kizbra-related exceptions; includes a
    "details" attribute for whatever error-related info.
    """
    def __init__(self, msg, **kwargs):
        self.details = KizbraNamespace(**kwargs)
        super().__init__(msg)


class ANDError(KizbraException):
    pass


class ORError(KizbraException):
    pass


class XORError(KizbraException):
    pass


class RequirementError(KizbraException):
    pass
