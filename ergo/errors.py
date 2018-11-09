from .misc import ErgoNamespace


class ErgoException(Exception):
    """
    Base class for ergo-related exceptions; includes a
    "details" attribute for whatever error-related info.
    """
    def __init__(self, msg, **kwargs):
        self.details = ErgoNamespace(**kwargs)
        super().__init__(msg)


class ANDError(ErgoException):
    pass


class ORError(ErgoException):
    pass


class XORError(ErgoException):
    pass


class RequirementError(ErgoException):
    pass
