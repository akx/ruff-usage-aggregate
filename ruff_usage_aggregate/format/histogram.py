import statistics
from collections import Counter
from io import StringIO

from ruff_usage_aggregate.format.helpers import format_bar


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
        print("## Histogram\n", file=sio)
        print("| Bin | Count | % | Bar |", file=sio)
        print("| --- | --- | --- | --- |", file=sio)
        for i, (count, edge) in enumerate(zip(counts, edges, strict=False)):
            next_edge = edges[i + 1] if i + 1 < len(edges) else edge + 1
            bar = format_bar(count, max_count, bar_width)
            histo_bin = f"{edge:.0f}..{next_edge:.0f}"
            print(
                f"| {histo_bin} | {count} | ",
                f"{count / len(flat_counter):.1%} | `{bar}` |",
                file=sio,
                sep="",
            )
        print(file=sio)
    except ImportError:
        pass
