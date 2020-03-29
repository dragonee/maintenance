"""
Get lengths (in full seconds) of all videos present in a directory.

Usage:
    video-lengths [-f FORMAT] [-c CACHE] DIRECTORY
    video-lengths -h | --help
    video-lengths --version

Options:
    -f FORMAT   Format - plain or json [default: plain].
    -c CACHE    Cache lengths. Assume files don't change.
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = '1.0'

from docopt import docopt


def main():
    arguments = docopt(__doc__, version=VERSION)