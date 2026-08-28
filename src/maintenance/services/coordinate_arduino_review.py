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

from pathlib import Path

from ..config.coordinate import CoordinateConfigFile
from ..arduino_api import Message

from ..strings import _regex_splitter

from itertools import chain, repeat
from functools import partial, reduce

from ..functional import compose, changes


def get_device_by_path(device):
    p = Path(device)

    return p if p.exists() else None


def get_device_by_patterns(patterns):
    suitable_paths = chain(*(glob.glob(pattern) for pattern in patterns))

    return next(map(Path, suitable_paths), None)


def find_suitable_device(device, patterns):
    found = get_device_by_path(device) or get_device_by_patterns(patterns)

    if not found:
        raise FileNotFoundError("There is no device under {} and {}".format(device, ', '.join(patterns)))

    return found


def get_redis_connection_from_pool(pool):
    return redis.Redis(connection_pool=pool)


def look_after_errors(previous_errors, f):
    try:
        f()
    except BaseException as e:
        if not previous_errors or str(e) != str(previous_errors[0]):
            print("Error: {}".format(e))

        time.sleep(4)

        return [e] + previous_errors[:9]

    return previous_errors


def device_to_serial(device_name):
    return serial.Serial(str(device_name), timeout=1.0)


def lock_values_to_message(lock_values, flatten=False):
    if flatten:
        return Message.led(any(lock_values))

    return Message.led(*lock_values)


def observe_locks(r, locks, flatten=False, interval=1):
    "Yield the message describing the state of locks, once every interval."
    while True:
        lock_values = [r.exists(l) for l in locks]

        yield lock_values_to_message(lock_values, flatten=flatten)

        time.sleep(interval)


def do_loop(request_serial, request_redis, locks=None, flatten=False):
    with request_redis() as r:
        with request_serial() as ser:
            for val in changes(observe_locks(r, locks, flatten=flatten)):
                ser.write(val)


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

    pool = redis.ConnectionPool(host=conf.server)

    if len(locks) > 8:
        raise ValueError("Too many locks to watch!")

    def configured_find_suitable_device():
        return find_suitable_device(device, patterns)

    def requests_redis():
        return get_redis_connection_from_pool(pool)

    takes_serial = compose(
        device_to_serial,
        configured_find_suitable_device,
    )

    configured_do_loop = partial(
        do_loop,
        takes_serial,
        requests_redis,
        locks=locks,
        flatten=flatten
    )

    reduce(look_after_errors, repeat(configured_do_loop), [])
