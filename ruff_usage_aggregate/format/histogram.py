import statistics
from collections import Counter
from io import StringIO


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


def format_stats_and_histogram(sio: StringIO, counter: Counter, bar_width=20, bins=10):
    flat_counter = [value for value, count in counter.items() for _ in range(count)]
    mean = statistics.mean(flat_counter)
    median = statistics.median(flat_counter)
    print(f"Mean: {mean:.2f} / Median: {median:.2f}", file=sio)
    print(file=sio)
    try:
        import numpy

        counts, edges = numpy.histogram(flat_counter, bins=bins)
        max_count = max(counts)
        for i, (count, edge) in enumerate(zip(counts, edges, strict=False)):
            next_edge = edges[i + 1] if i + 1 < len(edges) else edge + 1
            bar = format_bar(count, max_count, bar_width)
            print(f"{bar} | {edge:.0f}..{next_edge:.0f}: {count}  ", file=sio)
        print(file=sio)
    except ImportError:
        pass
