"""Threading admin panel module."""
import logging
import time
from functools import partial
from signal import SIGTSTP, pthread_kill
from threading import Thread
from typing import List

logger = logging.getLogger(__name__)


def wait_for_tasks(tasks: List[Thread], timeout=10):  # noqa: D103
    start = time.time()
    for p in tasks:
        p.start()
    while time.time() - start <= timeout:
        if not any([p.is_alive() for p in tasks]):
            break
        time.sleep(0.1)  # Just to avoid hogging the CPU
    else:
        for p in tasks:
            p.join()
            if p.is_alive():
                pthread_kill(p.ident, SIGTSTP)


def runs_in_background(args, timeout=10):  # noqa: D103
    return [run_in_background(t, a, k, timeout, False) for t, a, k in args]


def run_in_background(func, args=None, kwargs=None, timeout=10, join=True):  # noqa: D103
    def _run(f, *a, **kw):
        try:
            f(*a, **kw)
        except Exception as e:
            logger.exception(e)

    t = Thread(target=partial(_run, func), args=args or [], kwargs=kwargs or {})
    if join:
        wait_for_tasks([t], timeout)
    else:
        return t
