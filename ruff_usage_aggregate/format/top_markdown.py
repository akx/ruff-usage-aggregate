from __future__ import annotations

from collections import Counter, defaultdict
from io import StringIO

from ruff_usage_aggregate.constants import UNSET
from ruff_usage_aggregate.format.helpers import format_bar
from ruff_usage_aggregate.format.histogram import format_stats_and_histogram
from ruff_usage_aggregate.models import ScanResult


def format_values(values):
    return ", ".join(str(value) for value in sorted(values))


def format_counters(
    sio: StringIO,
    counters: list[Counter],
    cutoff=15,
    total_count: int | None = None,
    show_unset_as_value: bool = False,
):
    # Merge counters.
    counter = Counter()
    for c in counters:
        counter.update(c)
    unset_count = counter.pop(UNSET, 0)

    if all(isinstance(name, int) for name in counter):
        # All keys are integers, so we can format as a histogram instead.
        format_stats_and_histogram(sio, counter)

    format_table_and_rest(
        sio,
        counter,
        cutoff,
        total_count=total_count,
        show_unset_as_value=show_unset_as_value,
        unset_count=unset_count,
    )

    if unset_count and not show_unset_as_value:
        print("Unset:", unset_count, file=sio)
    print(file=sio)


def format_table_and_rest(
    sio: StringIO,
    counter: Counter,
    cutoff: int,
    *,
    total_count: int | None = None,
    show_unset_as_value: bool = False,
    unset_count: int,
):
    sorted_multi = defaultdict(set)
    for name, count in counter.items():
        sorted_multi[count].add(name)
    if show_unset_as_value:
        sorted_multi[unset_count].add(UNSET)
    sorted_counter = [(names, count) for (count, names) in sorted(sorted_multi.items(), reverse=True)]
    if total_count:
        print("| Name | Count | % |", file=sio)
        print("| ---- | ----- | - |", file=sio)
    else:
        print("| Name | Count |", file=sio)
        print("| ---- | ----- |", file=sio)
    for names, count in sorted_counter[:cutoff]:
        if total_count:
            bar = format_bar(count, total_count, 20)
            print(f"| {format_values(names)} | {count} | {count / total_count:.1%} {bar} |", file=sio)
        else:
            print(f"| {format_values(names)} | {count} |", file=sio)
    print(file=sio)
    rest = "; ".join(f"{format_values(names)} ({count})" for names, count in sorted_counter[cutoff:])
    if rest:
        print("Other values:", rest, file=sio)
        print(file=sio)


def format_top_markdown(sr: ScanResult) -> str:
    sio = StringIO()
    n = len(sr.configs)
    print(f"Results for {n} TOML files", file=sio)
    print(file=sio)
    format_aggregates(sio, sr)
    # format_value_sets(sio, sr)
    return sio.getvalue()


def format_aggregates(sio, sr: ScanResult):
    n = len(sr.configs)
    agg = sr.aggregate()
    print("# Top select/extend-select items\n", file=sio)
    format_counters(sio, [agg["select"], agg["extend_select"]])
    print("# Top ignore/extend-ignore items\n", file=sio)
    format_counters(sio, [agg["ignore"], agg["extend_ignore"]])
    print("# Top fixable items\n", file=sio)
    format_counters(sio, [agg["fixable"]])
    print("# Top unfixable items\n", file=sio)
    format_counters(sio, [agg["unfixable"]])
    print("# Line length\n", file=sio)
    format_counters(sio, [agg["line_length"]], show_unset_as_value=True, total_count=n)
    print("# Target version\n", file=sio)
    format_counters(sio, [agg["target_version"]], show_unset_as_value=True, total_count=n)
    print("# Fields set in configuration\n", file=sio)
    format_counters(sio, [agg["fields_set"]], total_count=n)
