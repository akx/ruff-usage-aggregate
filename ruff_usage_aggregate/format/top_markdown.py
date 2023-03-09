from __future__ import annotations

from collections import Counter, defaultdict
from io import StringIO

from ruff_usage_aggregate.constants import UNSET
from ruff_usage_aggregate.format.helpers import format_bar
from ruff_usage_aggregate.format.histogram import format_stats_and_histogram
from ruff_usage_aggregate.models import ScanResult


def format_value_atom(value):
    if isinstance(value, set | frozenset):
        if not value:
            return "(empty set)"
        return f"{{{format_values(value)}}}"
    return str(value)


def format_values(values):
    return ", ".join(format_value_atom(value) for value in sorted(values))


def format_counters(
    sio: StringIO,
    counters: list[Counter],
    top_table_count=15,
    total_count: int | None = None,
    show_unset_as_value: bool = False,
    show_other_values: bool = True,
    top_table_minimum_count: int = 0,
):
    # Merge counters.
    counter = Counter()
    for c in counters:
        counter.update(c)
    unset_count = counter.pop(UNSET, 0)

    if total_count is None:
        total_count = sum(counter.values())

    if all(isinstance(name, int) for name in counter):
        # All keys are integers, so we can format as a histogram instead.
        format_stats_and_histogram(sio, counter)
        print("## Values\n", file=sio)

    format_table_and_rest(
        sio,
        counter,
        top_table_count,
        total_count=total_count,
        show_unset_as_value=show_unset_as_value,
        show_other_values=show_other_values,
        unset_count=unset_count,
        top_table_minimum_count=top_table_minimum_count,
    )

    if unset_count and not show_unset_as_value:
        print("Unset:", unset_count, file=sio)
    print(file=sio)


def format_table_and_rest(
    sio: StringIO,
    counter: Counter,
    top_table_count: int,
    *,
    total_count: int | None = None,
    show_unset_as_value: bool = False,
    show_other_values: bool = True,
    unset_count: int,
    top_table_minimum_count: int = 0,
):
    # Group the counter so we collate values with the same count into one row in the table.
    sorted_multi = defaultdict(set)
    for value, count in counter.items():
        sorted_multi[count].add(value)
    if show_unset_as_value:
        sorted_multi[unset_count].add(UNSET)
    sorted_counter = [(values, count) for (count, values) in sorted(sorted_multi.items(), reverse=True)]

    if total_count:
        print(f"| Name | Count | % of {total_count} |", file=sio)
        print("| ---- | ----- | - |", file=sio)
    else:
        print("| Name | Count |", file=sio)
        print("| ---- | ----- |", file=sio)

    for values, count in sorted_counter[:top_table_count]:
        if count < top_table_minimum_count:
            break
        multi_count = count * len(values)
        if len(values) != 1:
            formatted_count = f"{count} ({multi_count})"
        else:
            formatted_count = str(count)
        if total_count:
            bar = format_bar(count, total_count, 15)
            print(f"| {format_values(values)} | {formatted_count} | {count / total_count:.1%} {bar} |", file=sio)
        else:
            print(f"| {format_values(values)} | {formatted_count} |", file=sio)
    print(file=sio)
    if show_other_values:
        rest = "; ".join(f"{format_values(values)} ({count})" for values, count in sorted_counter[top_table_count:])
        if rest:
            print("Other values:", rest, file=sio)
            print(file=sio)


def format_top_markdown(sr: ScanResult) -> str:
    sio = StringIO()
    n = len(sr.configs)
    print(f"Results for {n} TOML files", file=sio)
    print(file=sio)
    format_aggregates(sio, sr)
    format_value_sets(sio, sr)
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


def format_value_sets(sio, sr: ScanResult):
    vsc = sr.get_value_set_counters()
    print("# Top select/extend-select sets\n", file=sio)
    format_counters(
        sio,
        [vsc["select"], vsc["extend_select"]],
        show_other_values=False,
        top_table_minimum_count=2,
    )
    print("# Top ignore/extend-ignore sets\n", file=sio)
    format_counters(
        sio,
        [vsc["ignore"], vsc["extend_ignore"]],
        show_other_values=False,
        top_table_minimum_count=2,
    )
    print("# Top fixable sets\n", file=sio)
    format_counters(sio, [vsc["fixable"]])
    print("# Top unfixable sets\n", file=sio)
    format_counters(sio, [vsc["unfixable"]])
    print("# Top configuration field sets\n", file=sio)
    format_counters(sio, [vsc["fields_set"]], show_other_values=False, top_table_count=10)
