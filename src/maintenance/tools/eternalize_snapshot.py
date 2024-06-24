#!/usr/bin/env python3
"""
Make a directory snapshot on eternalize server storage.

Usage:
    eternalize [options] DIRECTORY TARGET

By default this utility eternalizes a directory adding a suffix of date
added (on MacOS X) for first and last file, e.g.:

Downloads_2020-01-20_2021-06-12

Then it removes files that are more than 30 days old, unless specified
otherwise by --days option.

Options:
    -p          Preserve directory (do not remove files).
    --days DAYS  Use specific value for days [default: 30].
    -s SERVER   Specify server configuration.
    -h, --help  Display this text.
    --version   Display version information.
"""

VERSION = '1.0'

import json
import shutil
import codecs
import subprocess
import sys

from pathlib import Path
from pprint import pprint

from io import BytesIO

from itertools import chain, islice, repeat
from operator import itemgetter

from docopt import docopt

from fabric import Connection
from ..transfer import Transfer

from ..config.eternalize import EternalizeConfigFile

from datetime import datetime, timedelta
import pytz

def trim_middle(s, l=100):
    if len(s) > l - 2:
        return s[:l//2 - 1] + '..' + s[-(l//2 + 1):]
    
    return s

def get_added_time_for_directory_items(path):
    count = 1

    for x in path.iterdir():
        if x.name.startswith('.'):
            continue

        f = path/x

        o = subprocess.check_output([
            'mdls', '-name', 'kMDItemDateAdded', '-raw', '--', str(f)
        ]).decode('utf-8')

        if 'null' in o:
            o = max(
                datetime.fromtimestamp(f.stat().st_mtime),
                datetime.fromtimestamp(f.stat().st_ctime)
            )

            o = pytz.utc.localize(o)
        else:
            o = datetime.strptime(o, '%Y-%m-%d %H:%M:%S %z')

        s = '[{0}] {1} loading\r'.format(count, trim_middle(str(x.name)).rjust(100)).rjust(106)

        sys.stdout.write(s)

        count += 1

        yield (f, o)


def get_new_name(name, results, pattern):
    minn = min(results, key=lambda x: x[1])
    maxx = max(results, key=lambda x: x[1])

    return pattern.format(
        name=name, 
        first_entry_date=minn[1].strftime('%Y-%m-%d'),
        last_entry_date=maxx[1].strftime('%Y-%m-%d')
    )


def remove_files(results, days):
    checked = pytz.utc.localize(datetime.now()) - timedelta(days=days)

    to_remove = [(p, t) for p,t in results if t < checked]

    s = sorted(to_remove, key=lambda x: x[1])

    print(list(s)[:10])
    print(list(s)[-10:])


def main():
    arguments = docopt(__doc__, version=VERSION)

    path = Path(arguments['DIRECTORY']).expanduser().resolve(strict=True)

    results = list(get_added_time_for_directory_items(path))

    print(results[-10:])

    new_name = get_new_name(
        path.name, 
        results,
        pattern="{name}_{last_entry_date}_{first_entry_date}"
    )

    print(new_name)

    eternalize_call = [
        'eternalize',
        '-m', new_name,
        '-p',
    ]

    if arguments['-s']:
        eternalize_call += ['-s', arguments['-s']]
    
    eternalize_call += [
        arguments['DIRECTORY'],
        arguments['TARGET'],
    ]

    print(eternalize_call)

    subprocess.check_call(eternalize_call)

    days = int(arguments['--days'])

    if not arguments['-p']:
        remove_files(results, days)
