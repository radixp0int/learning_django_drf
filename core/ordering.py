"""
Single source of truth for "what ordering did we actually apply?".

The paginator builds the ``sort`` block of the response envelope, but it runs
*after* filtering and has no visibility into what the ordering backend decided —
so on its own it can only guess by re-parsing the query string. That guess is
wrong whenever the client sends a field the view rejects, and wrong again for
``ListDataMixin`` views, which have no ``ordering`` attribute to fall back to.

Instead, whichever component resolves the ordering publishes its result here,
and the paginator reads it back. The DRF ``Request`` is the same object across
``filter_queryset()`` and ``paginate_queryset()``, so it makes a natural carrier.

This module deliberately imports nothing from ``core.filtering`` or
``core.pagination`` — both import *it*, and a neutral module keeps that
dependency acyclic.
"""

_ATTR = '_core_applied_ordering'


def set_applied_ordering(request, fields, is_default):
    """
    Record the ordering that was actually applied to this request.

    :param fields: ORM-style ordering terms, e.g. ``['-rating', 'created_at']``.
    :param is_default: ``True`` when the view's default ordering was used —
        either no ``?sort=`` was sent, or every field in it was rejected.
    """
    setattr(request, _ATTR, {'fields': list(fields or []), 'default': bool(is_default)})


def get_applied_ordering(request):
    """
    Return what was published for this request, or ``None`` if nothing was.

    ``None`` means no ordering component ran — callers should fall back rather
    than assume the response was unsorted.
    """
    return getattr(request, _ATTR, None)


def describe(term):
    """Translate an ORM term into envelope form: ``'-rating'`` -> field/direction."""
    if term.startswith('-'):
        return {'field': term[1:], 'direction': 'desc'}
    return {'field': term, 'direction': 'asc'}
