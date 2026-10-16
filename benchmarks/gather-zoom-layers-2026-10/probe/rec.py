"""2.152 probe helpers: the record-load lock and streamed reads (ijson); one record at a time, never a whole load."""
import contextlib
import os
import time

import ijson

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/"
RECORDS = {
    "litolff": LIB + "beethoven5-litolff-mvt1-whole-20261014-night.record.json",
    "brahms": LIB + "brahms1-breitkopf-mvt1-whole-20261014-night.record.json",
    "brahms_p0p3": LIB + "brahms1-breitkopf-p0-p3-ink.record.json",
}
LOCK = LIB + ".record-load.lock"


@contextlib.contextmanager
def lock():
    while True:
        try:
            os.mkdir(LOCK)
            break
        except FileExistsError:
            time.sleep(10)
    try:
        yield
    finally:
        os.rmdir(LOCK)


def items(path, key):
    with open(path, "rb") as f:
        for it in ijson.items(f, "record.%s.item" % key, use_float=True):
            yield it
