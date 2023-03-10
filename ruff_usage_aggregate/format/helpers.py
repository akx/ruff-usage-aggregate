from __future__ import annotations

from typing import Any, TextIO


def format_bar(value: float, max_value: float, width: int) -> str:
    w = width * value / max_value
    w_i, w_f = int(w), w - int(w)
    bar = "\u2588" * w_i
    if w_f > 0.75:
        bar += "\u258A"
    elif w_f > 0.5:
        bar += "\u258C"
    elif w_f > 0.25:
        bar += "\u258E"
    return bar.ljust(width, "\u2581")


def format_markdown_table(sio: TextIO, data: list[list[Any]], headers: list[str] | None = None) -> None:
    if headers:
        print(f"| {' | '.join(headers)} |", file=sio)
        print(f"| {' | '.join('---' for _ in headers)} |", file=sio)
    for row in data:
        print("| {} |".format(" | ".join(str(cell) for cell in row)), file=sio)
    print(file=sio)
