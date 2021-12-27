"""
Monitor status of specific Redis locks and communicate it to Arduino.

Run with supervisor, as it doesn't daemonize or check for its health.

Usage:
    coordinate-arduino [-d DEVICE] [-s DEVICES] [-f] LOCKS...
    coordinate-arduino -h | --help
    coordinate-arduino --version

LOCKS are an ordered list of Redis keys to poll.

Options:
    -f          Flatten all locks to the least-significant bit.
    -d DEVICE   Device to communicate with Arduino [default: /dev/ttyACM0].
    -s DEVICES  Scan for available devices with glob patterns.
    -h, --help  Display this message.
    --version   Show version information.

"""

VERSION = 1.0


from docopt import docopt
import serial
import time
import redis

import glob

import time

from pathlib import Path

from ..config.coordinate import CoordinateConfigFile
from ..arduino_api import Message

from ..strings import _regex_splitter

from itertools import chain, repeat
from functools import partial, reduce

from ..functional import compose


def find_suitable_device(device, patterns):
    p = Path(device)

    if p.exists():
        return p

    suitable_paths = chain(*(glob.glob(pattern) for pattern in patterns))

    try:
        return next(map(lambda x: Path(x), suitable_paths))
    except StopIteration:
        raise FileNotFoundError("There is no device under {} and {}".format(device, ', '.join(patterns)))


def get_redis_connection_from_pool(pool):
    return redis.Redis(connection_pool=pool)


def look_after_errors(previous_errors, f):
    try:
        f()
    except BaseException as e:
        if len(previous_errors) == 0 or str(e) != str(previous_errors[0]):
            print("Error: {}".format(e))

        time.sleep(4)

        return tuple([e]) + previous_errors[:9]

    return previous_errors


def device_to_serial(device_name):
    return serial.Serial(str(device_name), timeout=1.0)


def do_loop(request_serial, request_redis, locks=None, flatten=False):
    with request_redis() as r:
        with request_serial() as ser:
            lastval = 0
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


def main():
    arguments = docopt(__doc__, version=VERSION)

    device = arguments['-d']
    flatten = arguments['-f']

    if arguments['-s']:
        patterns = _regex_splitter.split(arguments['-s'])
    else:
        patterns = []

    locks = arguments['LOCKS']

    conf = CoordinateConfigFile()

    pool = redis.ConnectionPool(host=conf.server, password=conf.password)

    if len(locks) > 8:
        raise ValueError("Too many locks to watch!")

    configured_find_suitable_device = partial(find_suitable_device, device, patterns)

    takes_serial = partial(compose(
        device_to_serial,
        lambda _: configured_find_suitable_device()
    ), None)

    requests_redis = partial(get_redis_connection_from_pool, pool)

    configured_do_loop = partial(
        do_loop,
        takes_serial,
        requests_redis,
        locks=locks,
        flatten=flatten
    )

    reduce(look_after_errors, repeat(configured_do_loop), tuple())
