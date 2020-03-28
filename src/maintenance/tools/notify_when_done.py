"""
Call specific process. On finish, notify via Pushover API.

Usage:
    notify-when-done [options] [--] COMMAND...

Options:
    -p          High priority (this message will pop on phone).
    -m MESSAGE  Print specific message.
    --version   Show version information.
    -h, --help  Show this message.
"""

VERSION = '1.0'

from docopt import docopt
from functools import partial

from ..pushover import notify

import subprocess
import os


def call_process_then_notify(arguments, message=None, priority=None):
    return_value = subprocess.call(arguments)

    if return_value != 0:
        default_message = "Process {cmdline} has finished with code {status}."
    else:
        default_message = "Process {cmdline} has finished successfully."


    message = (message or default_message).format(
        cmdline=' '.join(arguments),
        status=str(return_value)
    )

    notify(
        message,
        priority=priority
    )


def main():
    arguments = docopt(__doc__, version=VERSION)

    call_process_then_notify(
        arguments['COMMAND'],
        arguments['-m'],
        1 if arguments['-p'] else 0
    )
