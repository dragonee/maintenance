#!/usr/bin/env python3

"""
Send a message to Arduino Coordinate device.

Usage:
    arduino [-d DEVICE] relay [RELAYS...]
    arduino [-d DEVICE] led [LEDS...]
    arduino -h | --help
    arduino --version

RELAYS can be from {0, 1}
LEDS can be from {0, 1, 2, 3}

Options:
    -d DEVICE   Device to communicate with Arduino [default: /dev/ttyACM0].
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = '1.0'


from docopt import docopt

import serial

from ..arduino_api import Message

def list_from_indices(indices):
    if not indices:
        return []

    indices = [int(x) for x in indices]

    return [x in indices for x in range(max(indices) + 1)]

def main():
    arguments = docopt(__doc__, version=VERSION)

    device = arguments['-d']

    with serial.Serial(device) as ser:
        if arguments['relay']:
            relays = list_from_indices(arguments['RELAYS'])

            ser.write(Message.relay(*relays))
            
        elif arguments['led']:
            leds = list_from_indices(arguments['LEDS'])

            ser.write(Message.led(*leds))
