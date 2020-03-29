"""
Get feed of NUMBER minutes of video files from remote directory.

Download Watch Later videos with yt-download-watch-later.

Usage:
    video-feed [-n NUMBER] DIRECTORY
    video-feed -h | --help
    video-feed --version

Options:
    -n NUMBER   Download enough files to satisfy this period [default: 60].
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = '1.0'

from docopt import docopt


def main():
    arguments = docopt(__doc__, version=VERSION)