#!/usr/bin/env python3
"""
Resolve conflicts when there are two versions of a file/directory.

Usage:
    eternalize-resolve-conflict MOVE_FROM MOVE_TO

Options:
    -h, --help  Display this text.
    --version   Display version information.
"""

VERSION = '1.0'

from pathlib import Path

from docopt import docopt

import subprocess
import shutil

def main():
    arguments = docopt(__doc__, version=VERSION)

    file = Path(arguments['MOVE_FROM']).expanduser().resolve(strict=True)
    target_path = Path(arguments['MOVE_TO']).expanduser().resolve(strict=True)


    if file.is_dir() and target_path.is_file():
        raise ValueError("{} is directory and {} is file.".format(str(file), str(target_path)))

    if file.is_file() and target_path.is_dir():
        raise ValueError("{} is file and {} is directory.".format(str(file), str(target_path)))

    if file.is_file():
        if file.stat().st_mtime > target_path.stat().st_mtime:
            file.rename(target_path)
        else:
            file.unlink()

    elif file.is_dir():
        args = [
            'rsync', '-avzs',
            '--progress',
            '{}/'.format(file),
            '{}/'.format(target_path)
        ]

        subprocess.check_call(args)

        shutil.rmtree(file)
