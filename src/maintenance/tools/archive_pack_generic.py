#!/usr/bin/env python3

"""
Pack a generic directory.

Usage:
    archive-pack-generic [-o OUTPUT] -m META_DIR DIR
    archive-pack-generic --check DIR
    archive-pack-generic -h | --help
    archive-pack-generic --version

Options:
    --check         Check if directory is a Wordpress instalation, return 0..1.
    -m META_DIR     Use this directory for meta storage.
    -o OUTPUT       Write archive to this file.
    --db DATABASES  A comma-separated list of databases.
    -h, --help      Display this message.
    --version       Show version information.
"""

VERSION = '1.0'

from docopt import docopt

from pathlib import Path

import subprocess


def main():
    arguments = docopt(__doc__, version=VERSION)

    path = Path(arguments['DIR']).resolve(strict=True)

    if arguments['--check']:
        print('0.1')
        return

    meta = Path(arguments['-m'])

    output = arguments['-o'] or path.parent/"{}.tar.gz".format(path.name)

    print('compress: create archive at {}'.format(output))

    subprocess.check_call([
        'archive-compress', '-v',
        '-f', 'gz',
        '-m', str(meta),
        str(path),
        str(output)
    ])

