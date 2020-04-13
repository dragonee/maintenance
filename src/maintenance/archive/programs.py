import os

from pathlib import Path

from itertools import chain
from functools import partial

from ..functional import compose


def find_programs_in_directory_startswith(prefix, dir):
    if not dir.exists():
        return []

    return filter(lambda x: x.name.startswith(prefix), dir.iterdir())


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