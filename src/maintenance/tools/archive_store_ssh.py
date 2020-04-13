"""
Store a file in the remote storage.

Usage:
    archive-store-ssh [options] FILE
    archive-store-ssh --help
    archive-store-ssh --version

Options:
    -r REMOTE  Put file in the.
    --help     Display this message.
    --version  Display version information.
"""

VERSION = '1.0'


import subprocess

from pathlib import Path

from docopt import docopt

from ..config.archive_storage import SSHConfigFile

from fabric import Connection
from ..transfer import Transfer


def main():
    arguments = docopt(__doc__, version=VERSION)

    file = Path(arguments['FILE']).expanduser().resolve(strict=True)

    conf = SSHConfigFile(arguments['-r'])

    c = Connection(conf.default_server, user=conf.default_user)
    t = Transfer(c)

    p = Path(conf.default_directory) / file.name

    t.rsync_put(file, p)
