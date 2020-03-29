"""
Monitor status of specific Redis locks and communicate it to Arduino.

Run with supervisor, as it doesn't daemonize or check for its health.

Usage:
    coordinate-arduino [-d DEVICE] LOCKS...
    coordinate-arduino -h | --help
    coordinate-arduino --version

LOCKS are an ordered list of Redis keys to poll.

Options:
    -d DEVICE   Device to communicate with Arduino [default: /dev/ttyUSB0].
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = 1.0


from docopt import docopt


def main():
    arguments = docopt(__doc__, version=VERSION)