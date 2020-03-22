"""
Wait for specific process to finish, then notify via Pushover API.

Usage:
    notify-on-exit [options] PID [MESSAGE]

Options:
    -p          High priority (this message will pop on phone).
    -b          Run in background.
    --version   Show version information.
    -h, --help  Show this message.
"""

VERSION = '1.0'

from docopt import docopt
from functools import partial

from daemonize import Daemonize
from psutil import Process

from ..pushover import notify

import os


def wait_for_process_then_notify(pid, message=None, priority=None):
    process = Process(pid)

    default_message = "Process {} ({})  has finished.".format(
        ' '.join(process.cmdline()),
        pid
    )

    process.wait()

    notify(
        message or default_message,
        priority=priority
    )


def do_daemonize(callable):
    daemon = Daemonize(
        app='notify-on-exit',
        pid=os.devnull,
        action=callable
    )

    daemon.start()


def main():
    arguments = docopt(__doc__, version=VERSION)

    pid = int(arguments['PID'])

    callable = partial(
        wait_for_process_then_notify,
        pid,
        message=arguments['MESSAGE'],
        priority=1 if arguments['-p'] else 0
    )

    if arguments['-b']:
        do_daemonize(callable)
    else:
        callable()
