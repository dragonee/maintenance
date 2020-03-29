"""
Get lengths (in full seconds) of all videos present in a directory.

Usage:
    video-lengths [-f FORMAT] [-c CACHE] DIRECTORY
    video-lengths -h | --help
    video-lengths --version

Options:
    -f FORMAT   Format - text or json [default: text].
    -c CACHE    Cache lengths. Assume files don't change.
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = '1.0'

from docopt import docopt

import subprocess
import json
import glob
import os, sys

from itertools import chain

from ..functional import compose


def lengths_to_json(dct):
    return json.dumps(dct)


def lengths_to_text(dct):
    return "\n".join([
        "{} {}".format(v, k) for k, v in dct.items()
    ])


def probe_video_file(f, ffprobe='ffprobe'):
    name, size = f

    if size:
        return (name, size)

    try:
        output = subprocess.check_output([
            ffprobe, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', name
        ]).decode('ascii').strip()

    except subprocess.CalledProcessError as e:
        print("File {}: {}".format(name, e), file=sys.stderr)
        return None

    return (name, output.split('.')[0])


def main():
    arguments = docopt(__doc__, version=VERSION)

    if arguments['-f'] == 'text':
        format_function = lengths_to_text
    elif arguments['-f'] == 'json':
        format_function = lengths_to_json
    else:
        raise ValueError('-f option needs to be one of: text, json.')

    olddir = os.getcwd()

    os.chdir(arguments['DIRECTORY'])

    files = set(glob.glob('*'))
    items = {f: None for f in files}

    cache_file = None
    if arguments['-c']:
        cache_file = os.path.expanduser(arguments['-c'])


    if cache_file:
        try:
            with open(cache_file, 'r') as f:
                c_items = json.load(f)
                c_files = set(c_items.keys())

                items.update(
                    {k: v for k, v in c_items.items() if k in c_files & files}
                )
        except FileNotFoundError:
            pass

    items = dict(filter(None, map(probe_video_file, items.items())))

    if cache_file:
        with open(cache_file, 'w') as f:
            json.dump(items, f)

    print(format_function(items))

    os.chdir(olddir)

