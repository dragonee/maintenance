"""
Generate automatic command index from a module's docstring.

Usage:
    make-readme FILE
    make-readme --help
    make-readme --version


Parses the following tag (one per line):
    [command-name=path.to.module]

Works when module is installed (e.g. by pip install -e .)

Options:
    --help     Display this message.
    --version  Display version information.
"""

VERSION = '1.0'


import sys
import re

import subprocess
from multiprocessing import Pool

from docopt import docopt


pattern = re.compile(r'^\s*\[\$\s*([\w\-\_]+)\]\s*$')

TEXT = """
{title_heading} {command_name} ({version})

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


def concurrently_map_to_dict(f, keys):
    p = Pool()
    results = p.map(doc_for, keys)
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

        items = concurrently_map_to_dict(doc_for, to_process)

        f.seek(0)

        for line in f:
            m = pattern.match(line)

            if not m:
                sys.stdout.write(line)
                continue

            sys.stdout.write(items[m.group(1)])

