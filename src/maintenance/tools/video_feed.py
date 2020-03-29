"""
Get feed of NUMBER minutes of video files from remote directory.

Download Watch Later videos with yt-download-watch-later.

Usage:
    video-feed [-n NUMBER] [-c] [DIRECTORY]
    video-feed -h | --help
    video-feed --version

Options:
    -c          Check local and remote pool.
    -n NUMBER   Download enough files to satisfy this period [default: 60].
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = '1.0'

from docopt import docopt

import subprocess
import os
import json
import shutil
from fabric import Connection

from itertools import islice


from ..config.youtube_feed import YoutubeFeedConfigFile

def duration_in_minutes(items):
    return sum(map(int, items.values())) // 60


def find_minimal_item_set(items, limit):
    val = 0
    dct = {}

    for k, v in items.items():
        val += int(v)
        dct[k] = v

        if val // 60 > limit:
            return dct

    return items

def minutes_to_readable(min):
    if min < 60:
        return "0h {:02d}m".format(min)

    return "{}h {:02d}m".format(min // 60, min % 60)

def main():
    arguments = docopt(__doc__, version=VERSION)

    conf = YoutubeFeedConfigFile()

    number = int(arguments['-n'])

    video_lengths = shutil.which('video-lengths')

    dir = os.path.expanduser(arguments['DIRECTORY'] or conf.local_path)

    local_output = subprocess.check_output([
        video_lengths, '-c', '.cache', '-f', 'json', dir
    ])

    local_output = local_output.decode('utf-8').strip()

    local_duration = duration_in_minutes(json.loads(local_output))

    print("Local: {} available.".format(minutes_to_readable(local_duration)))

    with Connection(conf.host, user=conf.user) as c:
        result = c.run('video-lengths -c .cache -t -f json {}'.format(conf.remote_path), hide='stdout')

        remote_files = json.loads(result.stdout.strip())
        remote_duration = duration_in_minutes(remote_files)

        if remote_duration == 0:
            print("No new videos found. Exiting...")
            return

        print("Remote: {} available.".format(minutes_to_readable(remote_duration)))

        if local_duration > number or arguments['-c']:
            print("Nothing to do.")
            return

        remote_files = find_minimal_item_set(remote_files, number - local_duration)

        for item in remote_files.keys():
            print("Downloading {}...".format(item))

            c.get("{}/{}".format(conf.remote_path, item), os.path.join(dir, item))
            c.run("rm '{}/{}'".format(conf.remote_path, item))

