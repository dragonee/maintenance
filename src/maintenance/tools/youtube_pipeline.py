"""
Download Youtube Watch Later playlist to a local directory, eternalize it,
then remove playlist.

Usage:
    yt-download-watch-later [options]

Options:
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = 1.0

import subprocess
import shutil
import glob
import sys, os

import docopt

from ..config.youtube_pipeline import YoutubePipelineConfigFile

NETWORK_RESOURCE = 'network'
STORAGE_RESOURCE = 'storage'

def main():
    arguments = docopt.docopt(__doc__, version=VERSION)

    coordinate = shutil.which('coordinate')
    eternalize = shutil.which('eternalize')
    yt_remove_watchlater = shutil.which('yt-remove-watchlater')
    yt_dl = shutil.which('youtube-dl')

    if not all([coordinate, eternalize, yt_remove_watchlater, yt_dl]):
        print([coordinate, eternalize, yt_remove_watchlater, yt_dl])
        raise RuntimeError("Not all tools were found.")

    conf = YoutubePipelineConfigFile()

    olddir = os.getcwd()

    os.chdir(conf.download_path)

    print("Downloading Watch Later...")

    # download Watch Later
    subprocess.check_call([
        coordinate, NETWORK_RESOURCE, '--',
        yt_dl, '--cookies', conf.cookies, 'https://www.youtube.com/playlist?list=WL'
    ])

    # check if there are any files
    files = glob.glob('*')
    no_files = len(files)

    if no_files == 0:
        print("No new videos downloaded.")
        return
    elif no_files == 1:
        print("Eternalizing...")
    else:
        print("Eternalizing {} files...".format(no_files))

    # eternalize files
    subprocess.check_call([
        coordinate, STORAGE_RESOURCE, '--',
        eternalize,
    ] + files + [conf.eternalize_target])

    print("Removing watch later items...")

    # remove watchlater
    subprocess.check_call([
        yt_remove_watchlater
    ])

    os.chdir(olddir)
