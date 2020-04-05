#!/usr/bin/env python3

"""
Compress meta directory and target directory into one tar archive.

Usage:
    archive-compress [-f FORMAT] [-m META_DIR] DIR FILE
    archive-compress -h | --help
    archive-compress --version

Options:
    -m META_DIR     Path to meta directory.
    -f FORMAT       Format: gz, bz2 or xz [default: xz]
"""

VERSION = '1.0'

from docopt import docopt

import tarfile


def reset(tarinfo):
    tarinfo.uid = tarinfo.gid = 0
    tarinfo.uname = tarinfo.gname = "root"
    return tarinfo


def main():
    arguments = docopt(__doc__, version=VERSION)

    mode = "w:{}".format(arguments['-f'])

    with tarfile.open(arguments['FILE'], mode) as t:
        t.add(arguments['DIR'], 'target', filter=reset)

        meta = arguments['-m']

        if meta:
            t.add(meta, 'meta', filter=reset)
