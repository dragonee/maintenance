
import functools
import collections
from itertools import islice

def compose(*functions):
    """Compose functions right to left.

    The innermost function is called with whatever arguments the composition
    was given, so it may take none, one or many; every other function takes
    the single value returned by its predecessor.
    """
    if not functions:
        return lambda x: x

    *outer, innermost = functions

    def composed(*args, **kwargs):
        return functools.reduce(
            lambda value, f: f(value),
            reversed(outer),
            innermost(*args, **kwargs)
        )

    return composed


def changes(iterable):
    "Yield only those values that differ from the previously yielded one."
    previous = object()

    for value in iterable:
        if value != previous:
            yield value

            previous = value


def consume(iterator, n=None):
    "Advance the iterator n-steps ahead. If n is none, consume entirely."
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        collections.deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(islice(iterator, n, n), None)
