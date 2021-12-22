"""
Generate automatic command index from a program.

Usage:
    make-readme [options] COMMAND

It outputs a Markdown section with program name, 
help and version information.

Works for any installed program that has --help
and --version options. Especially useful for Docopt.
It can be used with the following command to generate readme files:
    pip install -e .

Options:
    -h LEVEL, --heading LEVEL  Start from hLEVEL heading [default: 2].
    --help     Display this message.
    --version  Display version information.
"""

VERSION = '1.0'


import sys
import re

import subprocess

from docopt import docopt


TEXT = """{title_heading} {command_name} ({version})

```
{help_text}
```
"""


def doc_for(command_name, fmt_string=TEXT, title_heading="##"):
    version = subprocess.check_output([command_name, '--version']).strip().decode('utf-8')
    help_text = subprocess.check_output([command_name, '--help']).strip().decode('utf-8')

    return fmt_string.format(
        command_name=command_name,
        title_heading=title_heading,
        version=version,
        help_text=help_text
    )


def main():
    arguments = docopt(__doc__, version=VERSION)

    command = arguments['COMMAND']

    print(doc_for(
        command,
        title_heading='#' * int(arguments['--heading'])
    ), end='')
