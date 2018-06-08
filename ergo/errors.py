from ergo.misc import ErgoNamespace


class ErgoException(Exception):
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
