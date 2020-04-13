"""
Wait on specific resource lock and then run a command.

Usage:
    archive-check [options] DIRS...
    archive-check --help
    archive-check --version

Options:
    -a         Show all entries, even those with 0.0 score.
    -l         Use long format, even if one item was used.
    --help     Display this message.
    --version  Display version information.
"""

VERSION = '1.0'


import subprocess
import sys

from functools import partial
from docopt import docopt

from pathlib import Path

from ..functional import consume
from collections import namedtuple
from operator import itemgetter

from decimal import Decimal

from ..archive.programs import find_programs_startswith


check_dir_results = namedtuple(
    'check_dir_results',
    ('path', 'program', 'score'),
)

check_dir_results.path.__doc__ = "a pathlib.Path object"
check_dir_results.program.__doc__ = "a pathlib.Path object"
check_dir_results.score.__doc__ = "a decimal.Decimal score"


def check_single_program(dir, program):
    return Decimal(subprocess.check_output([
        program, '--check', dir
    ]).strip().decode('utf-8'))


def check_dir(programs, dir):
    check_single_program_with_dir = partial(check_single_program, dir)

    outputs = map(check_single_program_with_dir, programs)

    programs_with_outputs = zip(programs, outputs)

    best_fit_program_with_output = max(programs_with_outputs, key=itemgetter(1))

    return check_dir_results(dir, *best_fit_program_with_output)


def print_only_program(result):
    if result.score == 0:
        print("Did not find any candidate for {}...".format(result.path), file=sys.stderr)
        return

    print(result.program)


def print_full_response(result):
    if result.score == 0:
        print("{}:".format(result.path))

        return

    print("{}: {} ({})". format(result.path, result.program, result.score))


def main():
    arguments = docopt(__doc__, version=VERSION)

    dirs = arguments['DIRS']

    programs = find_programs_startswith('archive-pack-')

    check_dir_with_programs = partial(check_dir, programs)

    results = map(check_dir_with_programs, dirs)

    if not arguments['-a']:
        results = filter(lambda x: x.score > 0, results)

    results = list(results)

    if len(results) == 1 and not arguments['-l']:
        output_function = print_only_program
    else:
        output_function = print_full_response

    consume(map(output_function, results))

    if len(results) == 0:
        sys.exit(1)

    if not any(map(lambda x: x.score > 0, results)):
        sys.exit(1)

