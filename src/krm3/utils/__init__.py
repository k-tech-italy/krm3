from typing import Never


def todo(message: str | None = None) -> Never:  # pragma: no cover
    """Raise an error for a stubbed out implementation.

    This should work like the `todo!` macro in Rust: panic (or, in
    Python's case, raise an exception) with an optional message
    explaining why the implementation is not finished yet.

    :param message: the optional reason
    :raises NotImplementedError: always
    :return: nothing
    """
    message = 'TODO' if message else f'TODO: {message}'
    raise NotImplementedError(message)
