from collections import Counter, defaultdict
from io import StringIO

from ruff_usage_aggregate.constants import UNSET
from ruff_usage_aggregate.format.histogram import format_stats_and_histogram
from ruff_usage_aggregate.models import ScanResult


def format_values(values):
    return ", ".join(str(value) for value in sorted(values))


def format_counters(sio: StringIO, counters: list[Counter], cutoff=15):
    # Merge counters.
    counter = Counter()
    for c in counters:
        counter.update(c)
    unset_count = counter.pop(UNSET, 0)

    if all(isinstance(name, int) for name in counter):
        # All keys are integers, so we can format as a histogram instead.
        format_stats_and_histogram(sio, counter)

    format_table_and_rest(sio, counter, cutoff)

    if unset_count:
        print("Unset:", unset_count, file=sio)
    print(file=sio)


def format_table_and_rest(sio: StringIO, counter: Counter, cutoff: int):
    sorted_multi = defaultdict(set)
    for name, count in counter.items():
        sorted_multi[count].add(name)
    sorted_counter = [(names, count) for (count, names) in sorted(sorted_multi.items(), reverse=True)]
    print("| Name | Count |", file=sio)
    print("| ---- | ----- |", file=sio)
    for names, count in sorted_counter[:cutoff]:
        print(f"| {format_values(names)} | {count} |", file=sio)
    print(file=sio)
    rest = "; ".join(f"{format_values(names)} ({count})" for names, count in sorted_counter[cutoff:])
    if rest:
        print("Other values:", rest, file=sio)
        print(file=sio)


def format_top_markdown(sr: ScanResult) -> str:
    agg = sr.aggregate()
    sio = StringIO()
    print(f"Results for {len(sr.configs)} TOML files", file=sio)
    print(file=sio)
    print("# Top select/extend-select\n", file=sio)
    format_counters(sio, [agg["select"], agg["extend_select"]])
    print("# Top ignore/extend-ignore\n", file=sio)
    format_counters(sio, [agg["ignore"], agg["extend_ignore"]])
    print("# Top fixable\n", file=sio)
    format_counters(sio, [agg["fixable"]])
    print("# Top unfixable\n", file=sio)
    format_counters(sio, [agg["unfixable"]])
    print("# Line length\n", file=sio)
    format_counters(sio, [agg["line_length"]])
    print("# Target version\n", file=sio)
    format_counters(sio, [agg["target_version"]])
    print("# Fields set in configuration\n", file=sio)
    format_counters(sio, [agg["fields_set"]])
    return sio.getvalue()
