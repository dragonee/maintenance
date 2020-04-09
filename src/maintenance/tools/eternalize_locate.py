#!/usr/bin/env python3
"""
Move files from backup to another directory on remote server.

Usage:
    eternalize-locate [options] PATH TARGET

TARGET can be:
    Folder
    Folder/Directory, which will create a directory and put file inside
    Folder/*, which will try to match the closest directory

Options:
    -b BACKUP   Backup base path.
    -p PATTERN  Use the following pattern to find directory.
    -f FORMAT   Set output format (text, json) [default: text].
    -h, --help  Display this text.
    --version   Display version information.
"""

VERSION = '1.0'


import json

from pathlib import Path

from docopt import docopt

from difflib import SequenceMatcher


def resolve_pattern(target, pattern, real_path):
    if pattern == '*':
        matcher = SequenceMatcher(a=real_path.name)
        distance = 0.3
        directory = None

        for child in target.iterdir():
            if not child.is_dir():
                continue

            matcher.set_seq2(child.name)

            new_distance = matcher.ratio()

            if new_distance > distance:
                distance = new_distance
                directory = child

        if not directory:
            raise RuntimeError("Matching directory not found")

        return directory

    if pattern:
        return target/pattern

    return target


def locate(real_path, target_path, pattern):
    if pattern:
        try:
            target_path = resolve_pattern(target_path, pattern, real_path)
        except RuntimeError:
            return {
                'status': 'EINVAL',
                'from': str(real_path),
                'message': 'Could not find any matching path.'
            }

    target_file = target_path/real_path.name

    if not real_path.exists() and target_file.exists():
        return {
            'status': 'EMOVED',
            'from': str(real_path),
            'to': str(target_file),
        }

    if not real_path.exists():
        return {
            'status': 'ENOENT',
            'from': str(real_path),
            'to': str(target_file),
            'directory': str(target_path),
            'directory_exists': target_path.exists(),
        }

    if target_file.exists():
        return {
            'status': 'EEXIST',
            'from': str(real_path),
            'to': str(target_file),
            'files_differ': real_path.stat().st_size != target_file.stat().st_size,
        }

    return {
        'status': 'OK',
        'from': str(real_path),
        'to': str(target_file),
        'directory': str(target_path),
        'directory_exists': target_path.exists(),
    }


def output_json(response):
    return json.dumps(response)

def output_text(response):
    return "\n".join(["{}: {}".format(k, v) for k,v in response.items()])


def main():
    arguments = docopt(__doc__, version=VERSION)

    backup_path = arguments['-b']
    pattern = arguments['-p']

    file = arguments['PATH']
    target = arguments['TARGET']

    if backup_path:
        real_path = Path(backup_path) / Path(file)
    else:
        real_path = Path(file)

    real_path = real_path.expanduser().resolve()
    target_path = Path(target).expanduser().resolve(strict=True)

    response = locate(real_path, target_path, pattern)

    if arguments['-f'] == 'json':
        response = output_json(response)
    else:
        response = output_text(response)

    print(response)





