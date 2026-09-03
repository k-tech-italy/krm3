from pyoxr import OXRError


class AlreadyReimbursed(RuntimeError):
    """Raised when an expense has already been reimbursed."""



class RateConversionError(RuntimeError):
    """Error in converting rate."""

    def __init__(self, err: OXRError, *args) -> None:
        super().__init__(*args)
        if errmsg := getattr(err, 'description', None):
            self.message = errmsg
        else:
            self.message = str(err)

    def __str__(self) -> str:
        return self.message
