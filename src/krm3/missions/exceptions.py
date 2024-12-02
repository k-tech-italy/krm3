from pyoxr import OXRError


class AlreadyReimbursed(RuntimeError):
    """Raised when an expense has already been reimbursed."""
    pass


class RateConversionError(RuntimeError):
    """Error in converting rate."""

    def __init__(self, err: OXRError, *args):
        super().__init__(*args)
        if errmsg := getattr(err, 'description', None):
            self.message = errmsg
        else:
            self.message = str(err)

    def __str__(self):
        return self.message
