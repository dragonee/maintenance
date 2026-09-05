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

#: sysexits.h EX_CONFIG. The driver reads this as "nothing is set up here",
#: skips the upload and keeps the archive, rather than failing the run.
EX_CONFIG = 78


import subprocess
import sys

from pathlib import Path

from docopt import docopt

from ..config.archive_storage import SSHConfigFile, StorageNotConfigured

from fabric import Connection
from ..transfer import Transfer


def main():
    arguments = docopt(__doc__, version=VERSION)

    file = Path(arguments['FILE']).expanduser().resolve(strict=True)

    try:
        conf = SSHConfigFile(arguments['-r'])
    except StorageNotConfigured as e:
        print('archive-store-ssh: {}'.format(e), file=sys.stderr)
        sys.exit(EX_CONFIG)

    c = Connection(conf.default_server, user=conf.default_user)
    t = Transfer(c)

    p = Path(conf.default_directory) / file.name

    t.rsync_put(file, p)
