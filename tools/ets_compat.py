"""Compatibility shims for symbols removed from the ETS stack.

PY3-PORT: added. Nothing here is a Python 2 issue -- these are APIs that
Enthought removed or moved between Traits 4/Chaco 3 (what this codebase was
written against) and Traits 7/Chaco 6 (what installs today).
"""

from traits.api import HasTraits, HasPrivateTraits, HasStrictTraits


def _singleton_new(cls, *args, **traits):
    """Reproduces traits.has_traits._SingletonHasTraits.__new__.

    Traits dropped the Singleton* base classes in 6.0. The original semantics
    were: one instance per class, but `__init__` re-runs on every call. That
    second half is surprising, and code here relies on it, so it is preserved
    exactly rather than "fixed".
    """
    if '__instance__' not in cls.__dict__:
        cls.__instance__ = None
    if cls.__instance__ is None:
        cls.__instance__ = object.__new__(cls)
    return cls.__instance__


class SingletonHasTraits(HasTraits):
    """PY3-PORT: was traits.api.SingletonHasTraits, removed in Traits 6.0."""
    __new__ = _singleton_new


class SingletonHasPrivateTraits(HasPrivateTraits):
    """PY3-PORT: was traits.api.SingletonHasPrivateTraits, removed in Traits 6.0."""
    __new__ = _singleton_new


class SingletonHasStrictTraits(HasStrictTraits):
    """PY3-PORT: was traits.api.SingletonHasStrictTraits, removed in Traits 6.0."""
    __new__ = _singleton_new
