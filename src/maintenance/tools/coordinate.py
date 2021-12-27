"""
Wait on specific resource lock and then run a command.

Usage:
    coordinate [-h HOST] RESOURCE [--] COMMAND...
    coordinate --help
    coordinate --version

Options:
    -h HOST    Use specific Redis host.
    --help     Display this message.
    --version  Display version information.
"""

VERSION = '1.0'


import subprocess
import os, sys

from functools import partial

from docopt import docopt

import redis

from ..config.coordinate import CoordinateConfigFile

from ..redis.lock_thread import run_with_lock_thread


def main():
    arguments = docopt(__doc__, version=VERSION)

    resource = arguments['RESOURCE']
    command = arguments['COMMAND']

    config = CoordinateConfigFile()

    r = redis.Redis(arguments['-h'] or config.server, password=config.password)

    callable = partial(subprocess.call, command)

    run_with_lock_thread(r, callable, resource)