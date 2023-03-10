from __future__ import annotations

import contextlib
import json
import pathlib
from collections.abc import Iterable
from typing import IO


def write_jsonl(dest: pathlib.Path | IO, data: Iterable[dict]) -> int:
    last_line = None
    n = 0
    with _open_or_enter(dest, "w") as f:
        for datum in data:
            line = json.dumps(datum, sort_keys=True, ensure_ascii=False)
            if line != last_line:
                print(line, file=f)
                n += 1
                last_line = line
    return n


def _open_or_enter(dest, mode: str):
    if isinstance(dest, str | pathlib.Path):
        return pathlib.Path(dest).open(mode)
    return contextlib.nullcontext(dest)


def _error(line: str) -> dict:
    raise ValueError(f"Invalid JSONL line: {line!r}")


def read_jsonl(dest: pathlib.Path | IO, converter=_error) -> Iterable[dict]:
    with _open_or_enter(dest, "r") as f:
        for line in f:
            if line.startswith("{"):
                yield json.loads(line)
            else:
                yield converter(line)
