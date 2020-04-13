#!/usr/bin/env python3

"""
Compress meta directory and target directory into one tar archive.

Usage:
    archive-compress [options] DIR FILE
    archive-compress -h | --help
    archive-compress --version

Options:
    -v              Be verbose.
    -m META_DIR     Path to meta directory.
    -f FORMAT       Format: gz, bz2 or xz [default: gz]
    -h, --help      Display this message.
    --version       Show version information.
"""

VERSION = '1.0'

from docopt import docopt

import tarfile
import sys

from functools import partial

def compress(str, limit, replace='..'):
    l = len(str)

    if l <= limit:
        return str

    third = limit // 3

    return str[:third] + replace + str[-(limit - third - 2):]


def reset(tarinfo, verbose=False):
    if verbose:
        sys.stdout.write("{:72}\r".format(compress(tarinfo.name, 72)))

    tarinfo.uid = tarinfo.gid = 0
    tarinfo.uname = tarinfo.gname = "root"
    return tarinfo


def main():
    arguments = docopt(__doc__, version=VERSION)

    mode = "w:{}".format(arguments['-f'])

    with tarfile.open(arguments['FILE'], mode) as t:
        reset_with_options = partial(reset, verbose=arguments['-v'])

        t.add(arguments['DIR'], 'target', filter=reset_with_options)

        meta = arguments['-m']

        if meta:
            t.add(meta, 'meta', filter=reset_with_options)

    # Clear last entry
    if arguments['-v']:
        sys.stdout.write("{:72}\r".format(''))
