
# Base class: Inheriting all other errors from this makes it easier to turn all of them
# off if someone wishes to later down the road, without interfering with other modules' error messages.
class BaseValidateError(ValueError):
    pass

# Specific errors used in module
class GageTooLongError(BaseValidateError):
    pass

class NoDateSpecifiedError(BaseValidateError):
    pass

class MissingBandsError(BaseValidateError):
    pass



