import threading
import time

from ..threading import StoppableThread
from .lock import Lock

class LockThread(StoppableThread):
    def __init__(self, lock, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.lock = lock

    def run(self):
        while not self.stopped():
            time.sleep(1)

            if not self.lock.expires_soon():
                continue

            self.lock.extend()


def run_with_lock_thread(r, func, name):
    l = Lock(r, name)

    with Lock(r, name) as l:
        t1 = LockThread(l)
        t2 = threading.Thread(target=func)

        t1.start()
        t2.start()

        while t2.is_alive():
            t2.join(1)

            if not t1.is_alive():
                t1 = LockThread(l)
                t1.start()

        t1.stop()
        t1.join()