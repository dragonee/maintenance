import uuid
import time

import redis


class LockNotAcquired(RuntimeError):
    pass


class Lock:
    name = None
    expires = 30

    def __init__(self, r, name):
        self.r = r
        self.name = name
        self.value = str(uuid.uuid4())

    def acquire_once(self):
        result = self.r.set(
            self.name,
            self.value,
            ex=self.expires,
            nx=True
        )

        self.acquisition_time = time.time()

        return True if result else False

    def expires_soon(self):
        """Return true if less than half time remains for lock"""

        return time.time() > self.acquisition_time + (self.expires / 2)

    def acquire(self, timeout=None):
        if timeout:
            end = time.time() + timeout
            condition = lambda: time.time() < end
        else:
            condition = lambda: True

        while condition():
            result = self.acquire_once()

            if result:
                return True

        return False

    def acquired(self):
        return self.r.get(self.name) == self.value

    def extend(self, expires=None):
        expires = expires or self.expires

        with self.r.pipeline() as pipe:
            try:
                pipe.watch(self.name)
                value = pipe.get(self.name)

                value = value.decode('ascii')

                # If the value is not your own, this is a problem.
                if value != self.value:
                    raise LockNotAcquired("acquire lock first in order to extend it")

                pipe.multi()
                pipe.set(self.name, self.value, xx=True, ex=expires)
                pipe.execute()

                self.acquisition_time = time.time()

            except redis.WatchError:
                # value has change
                return False

        return True

    def release(self):
        with self.r.pipeline() as pipe:
            try:
                pipe.watch(self.name)
                value = pipe.get(self.name)

                value = value.decode('ascii')

                if value != self.value:
                    return True

                pipe.multi()
                pipe.delete(self.name)
                pipe.execute()
            except redis.WatchError:
                # value has changed, do nothing
                pass

        return True

    def __enter__(self):
        self.acquire()

        return self

    def __exit__(self, *args, **kwargs):
        self.release()