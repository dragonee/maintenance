"""
Monitor status of specific Redis locks and communicate it to Arduino.

Run with supervisor, as it doesn't daemonize or check for its health.

Usage:
    coordinate-arduino [-d DEVICE] [-f] LOCKS...
    coordinate-arduino -h | --help
    coordinate-arduino --version

LOCKS are an ordered list of Redis keys to poll.

Options:
    -f          Flatten all locks to the least-significant bit.
    -d DEVICE   Device to communicate with Arduino [default: /dev/ttyACM0].
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = 1.0


from docopt import docopt
import serial
import time
import redis

from ..config.coordinate import CoordinateConfigFile
from ..arduino_api import Message

def main():
    arguments = docopt(__doc__, version=VERSION)

    device = arguments['-d']
    flatten = arguments['-f']

    locks = arguments['LOCKS']

    conf = CoordinateConfigFile()

    if len(locks) > 8:
        raise ValueError("Too many locks to watch!")

    r = redis.Redis(conf.server)

    with serial.Serial(device, timeout=1.0) as ser:
        lastval = Message.led()
        ser.write(lastval)

        while True:
            val = 0

            lock_values = [r.exists(l) for l in locks]

            if flatten:
                val = Message.led(any(lock_values))
            else:
                val = Message.led(*lock_values)

            if val != lastval:
                ser.write(val)
                lastval = val

            time.sleep(1)
