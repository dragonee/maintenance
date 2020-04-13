"""
Package a specific directory, then store it in a storage.

Usage:
    archive [options] DIR [--] [ARGS...]
    archive --help
    archive --version

Options:
    -p         Preserve the directory.
    -s STORAGE  Use specific storage command [default: ssh]
    --help     Display this message.
    --version  Display version information.
"""

VERSION = '1.0'


import subprocess
import os, sys

import tempfile
import shutil

from pathlib import Path
from functools import partial
from ..functional import consume

from docopt import docopt

from ..archive.programs import find_programs_startswith
from ..console import ask_for


def call_teardown(path, program):
    subprocess.call([
        program, str(path)
    ])


def main():
    arguments = docopt(__doc__, version=VERSION)

    dir = Path(arguments['DIR']).expanduser().resolve(strict=True)

    meta_dir = Path(tempfile.mkdtemp(prefix='archive-m-{}'.format(dir.name[:19])))
    archive_dir = Path(tempfile.mkdtemp(prefix='archive-d-{}'.format(dir.name[:19])))

    archive_path = archive_dir/"{}.tar.gz".format(dir.name)

    try:
        # FIND packer

        program_name = Path(subprocess.check_output([
            'archive-check', str(dir)
        ]).strip().decode('utf-8'))

        print("Using {}".format(program_name))

        # PACK

        subprocess.check_call([
            str(program_name),
            '-o', str(archive_path),
            '-m', str(meta_dir),
            str(dir),
        ] + arguments['ARGS'])

        # CONFIRM if the archive was created successfully

        print("Do you want to proceed?")

        if not ask_for(['y', 't'], ['n', 'f']):
            return

        # STORAGE

        if 'archive-store-' in arguments['-s']:
            storage_program_name = arguments['-s']
        else:
            storage_program_name = 'archive-store-{}'.format(arguments['-s'])

        storage_program = shutil.which(storage_program_name)

        if storage_program is None:
            raise ValueError("Invalid storage program {}".format(storage_program_name))

        subprocess.check_call([
            storage_program,
            str(archive_path)
        ])

        # TEARDOWN

        if not arguments['-p']:
            teardown_programs = find_programs_startswith('archive-teardown-')

            call_teardown_on_path = partial(call_teardown, meta_dir)

            consume(map(call_teardown_on_path, teardown_programs))

            print("removing directory {}...".format(dir))
            shutil.rmtree(dir)

    finally:
        shutil.rmtree(meta_dir)
        shutil.rmtree(archive_dir)
