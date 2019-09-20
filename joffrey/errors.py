from .misc import JoffreyNamespace


class JoffreyException(Exception):
    """
    Base class for joffrey-related exceptions; includes a
    "details" attribute for whatever error-related info.
    """
    def __init__(self, msg, **kwargs):
        self.details = JoffreyNamespace(**kwargs)
        super().__init__(msg)


class ANDError(JoffreyException):
    pass


class ORError(JoffreyException):
    pass


class XORError(JoffreyException):
    pass


class RequirementError(JoffreyException):
    pass
