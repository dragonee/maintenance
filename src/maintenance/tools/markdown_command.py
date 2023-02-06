"""
Process a Markdown file, execute commands within 
and print file contents with executed commands' output.

Usage:
    markdown-command [options] FILE

The pattern for commands to be executed is:
    [$ command --with-options -and arguments]

Options:
    --help     Display this message.
    --version  Display version information.
"""

VERSION = '1.0.1'


import sys
import re

import shutil

import subprocess
from multiprocessing import Pool

from docopt import docopt

import shlex


pattern = re.compile(r'^\s*\[\$\s*([^\]]+)\]\s*$')


def run_cmd(command_string):
    return subprocess.check_output(
        shlex.split(command_string)
    ).decode('utf-8')


def concurrently_map_to_dict(f, keys):
    p = Pool()
    results = p.map(f, keys)
    p.close()

    return dict(zip(keys, results))


def main():
    arguments = docopt(__doc__, version=VERSION)

    file = arguments['FILE']

    with open(file, 'r') as f:
        to_process = []

        for line in f:
            m = pattern.match(line)

            if not m:
                continue

            to_process.append(m.group(1))

        items = concurrently_map_to_dict(run_cmd, to_process)

        f.seek(0)

        for line in f:
            m = pattern.match(line)

            if not m:
                sys.stdout.write(line)
                continue

            sys.stdout.write(items[m.group(1)])

