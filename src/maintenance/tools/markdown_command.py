"""
Process a Markdown file, execute commands within 
and print file contents with executed commands' output.

Usage:
    markdown-command [options] FILE

The pattern for commands to be executed is:
    [$ command --with-options -and arguments]

Options:
    -h, --help               Display this message.
    --version                Display version information.
    --dry-run                Do not execute commands, just print them.
    -O, --only-commands      Only run commands, do not print file contents.
    -C, --cwd PATH           Change to directory before running commands.
"""

VERSION = '1.1'


import sys
import re

import shutil

import subprocess
from multiprocessing import Pool

from docopt import docopt

from functools import partial

from pathlib import Path

import shlex


pattern = re.compile(r'\[\$\s*(?P<command>[^\]]+)\]')


def run_cmd(command_string, cwd=None):
    return subprocess.check_output(
        shlex.split(command_string),
        cwd=cwd
    ).decode('utf-8')


def concurrently_map_to_dict(f, keys):
    p = Pool()
    results = p.map(f, keys)
    p.close()

    return dict(zip(keys, results))


def main():
    arguments = docopt(__doc__, version=VERSION)

    file = Path(arguments['FILE'])

    with file.open('r') as f:
        to_process = []

        for line in f:
            m = pattern.search(line)

            if not m:
                continue

            inline = bool(line[:m.start()].strip() + line[m.end():].strip())

            to_process.append(m.group('command'))

        if arguments['--dry-run']:
            for cmd in to_process:
                print(cmd)

            return
        
        cwd = file.parent if not arguments['--cwd'] else arguments['--cwd']

        run_cmd_with_cwd = partial(run_cmd, cwd=cwd)

        items = concurrently_map_to_dict(run_cmd_with_cwd, to_process)

        if arguments['--only-commands']:
            for index, (cmd, output) in enumerate(items.items()):
                print(f'[{index + 1}/{len(items)}] {cmd}\n{output}')

            return

        f.seek(0)

        for line in f:
            m = pattern.search(line)

            if not m:
                sys.stdout.write(line)
                continue

            inline = bool(line[:m.start()].strip() + line[m.end():].strip())

            if not inline:
                sys.stdout.write(items[m.group('command')])
            else:
                sys.stdout.write(line[:m.start()] + items[m.group('command')].strip() + line[m.end():])

