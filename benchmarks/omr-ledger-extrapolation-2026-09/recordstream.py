"""Stream the top-level elements of one array inside a staged record.

⚠️ WHY NOT `json.load`. The shared Breitkopf record is 443 MB of
pretty-printed JSON; parsed whole it is several GB of Python objects, and a
probe that dies on the SECOND publisher is a probe that can only ever confirm
the first. This walks the array with `raw_decode`, holding the file text plus
one element at a time.

⚠️ It is deliberately NOT a JSON parser. It finds the array by its KEY and
then hands every element to the stdlib decoder, so a malformed record raises
rather than being silently half-read -- the failure this repo keeps paying for
is a filter that empties a file and looks exactly like an empty file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def stream_array(path: str | Path, key: str) -> Iterator[Any]:
    """Yield each element of the top-level array stored under `"<key>": [`.

    Raises KeyError when the key is absent -- never yields nothing quietly.
    """
    text = Path(path).read_text()
    needle = f'"{key}": ['
    i = text.find(needle)
    if i < 0:
        raise KeyError(f"{key!r} not found in {path}")
    i += len(needle)
    dec = json.JSONDecoder()
    n = len(text)
    while True:
        while i < n and text[i] in " \t\r\n,":
            i += 1
        if i >= n:
            raise ValueError(f"{key!r} array never closed in {path}")
        if text[i] == "]":
            return
        obj, i = dec.raw_decode(text, i)
        yield obj
