"""Reflection utilities module."""

import types
from functools import lru_cache
from inspect import isclass


@lru_cache(100)
def fqn(o, silent=False, from_module=None):
    """Return the fully qualified class name of an object or a class.

    :param o: object or class
    :return: class name
    """
    parts = []
    if isinstance(o, (str, bytes)):
        return o
    if not hasattr(o, '__module__'):
        if silent:
            return None
        raise ValueError('Invalid argument `%s` %s' % (type(o), o))
    parts.append(o.__module__)
    if isclass(o) or isinstance(o, types.FunctionType):
        parts.append(o.__name__)
    else:
        parts.append(o.__class__.__name__)
    return '.'.join(parts)


def package_name(c):  # noqa: D103
    return fqn(c).split('.')[0]


def classname(c):  # noqa: D103
    return fqn(c).split('.')[-1]
