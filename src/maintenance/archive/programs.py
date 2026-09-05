import os

from pathlib import Path

from itertools import chain
from functools import partial

from ..functional import compose


def is_runnable(path):
    "A file we could actually execute, not a directory that looks like one."
    return path.is_file() and os.access(str(path), os.X_OK)


def find_programs_in_directory_startswith(prefix, dir):
    if not dir.exists():
        return []

    return filter(
        lambda x: x.name.startswith(prefix) and is_runnable(x),
        dir.iterdir()
    )


def find_programs_startswith(prefix):
    dirs = os.environ['PATH'].split(os.pathsep)

    find_programs_in_directory_startswith_prefix = partial(
        find_programs_in_directory_startswith,
        prefix
    )

    dir_listings = map(compose(
        find_programs_in_directory_startswith_prefix,
        lambda x: Path(x)
    ), dirs)

    return list(chain(*dir_listings))