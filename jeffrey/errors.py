from .misc import JeffreyNamespace


class JeffreyException(Exception):
    """
    Base class for jeffrey-related exceptions; includes a
    "details" attribute for whatever error-related info.
    """
    def __init__(self, msg, **kwargs):
        self.details = JeffreyNamespace(**kwargs)
        super().__init__(msg)


class ANDError(JeffreyException):
    pass


class ORError(JeffreyException):
    pass


class XORError(JeffreyException):
    pass


class RequirementError(JeffreyException):
    pass
