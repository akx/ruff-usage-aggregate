import statistics
from collections import Counter
from io import StringIO

from ruff_usage_aggregate.format.helpers import format_bar, format_markdown_table


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
        headers = ["Bin", "Count", "%", "Bar"]
        data = []
        for i, (count, edge) in enumerate(zip(counts, edges, strict=False)):
            next_edge = edges[i + 1] if i + 1 < len(edges) else edge + 1
            data.append(
                [
                    f"{edge:.0f}..{next_edge:.0f}",
                    count,
                    f"{count / len(flat_counter):.1%}",
                    format_bar(count, max_count, bar_width),
                ],
            )
        format_markdown_table(sio, data, headers=headers)
    except ImportError:
        pass
