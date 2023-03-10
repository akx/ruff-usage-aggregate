from __future__ import annotations

from collections import Counter, defaultdict
from io import StringIO

from ruff_usage_aggregate.constants import UNSET
from ruff_usage_aggregate.format.helpers import format_bar, format_markdown_table
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
        if show_unset_as_value:
            total_count += unset_count

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
        headers = ["Name", "Count", f"% of {total_count}"]
    else:
        headers = ["Name", "Count"]

    data = []

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
            data.append([format_values(values), formatted_count, f"`{bar}` {count / total_count:.1%}"])
        else:
            data.append([format_values(values), formatted_count])

    format_markdown_table(sio, data, headers=headers)

    if show_other_values:
        rest = "; ".join(f"{format_values(values)} ({count})" for values, count in sorted_counter[top_table_count:])
        if rest:
            print("Other values:", rest, file=sio)
            print(file=sio)


def format_key_takeaways(sio, sr: ScanResult):
    no_fixable = sr.value_set_counters["fixable"].get(UNSET, 0) / sr.n_unique
    no_ignore = sr.value_set_counters["ignore"].get(UNSET, 0) / sr.n_unique
    no_select = sr.value_set_counters["select"].get(UNSET, 0) / sr.n_unique
    no_unfixable = sr.value_set_counters["unfixable"].get(UNSET, 0) / sr.n_unique
    format_markdown_table(
        sio,
        [
            ["Total TOML files", sr.n_total],
            ["Unique TOML files", sr.n_unique],
            ["Deduplicated TOML files", sr.n_deduplicated],
            ["No select", f"{no_select:.1%}"],
            ["No ignore", f"{no_ignore:.1%}"],
            ["No fixable", f"{no_fixable:.1%}"],
            ["No unfixable", f"{no_unfixable:.1%}"],
            ["Most popular configured Python version", sr.most_common_set_values["target_version"]],
            ["Median configured line length", sr.median_line_length],
            ["Most common unfixable", sr.most_common_set_values["unfixable"]],
            ["Most common ignore", sr.most_common_set_values["ignore"]],
            ["Most common select", sr.most_common_set_values["select"]],
        ],
        headers=["Name", "Value"],
    )


def format_markdown(sr: ScanResult) -> str:
    sio = StringIO()
    format_key_takeaways(sio, sr)
    format_aggregates(sio, sr)
    format_value_sets(sio, sr)
    return sio.getvalue()


def format_aggregates(sio, sr: ScanResult):
    n = sr.n_unique
    agg = sr.aggregated_data
    for heading, field in [
        ("Top select items", "select"),
        ("Top extend-select items", "extend_select"),
        ("Top ignore items", "ignore"),
        ("Top extend-ignore items", "extend_ignore"),
        ("Top fixable items", "fixable"),
        ("Top unfixable items", "unfixable"),
    ]:
        print(f"# {heading}\n", file=sio)
        format_counters(sio, [agg[field]])

    print("# Line length\n", file=sio)
    format_counters(sio, [agg["line_length"]], show_unset_as_value=True, total_count=n)
    print("# Target version\n", file=sio)
    format_counters(sio, [agg["target_version"]], show_unset_as_value=True, total_count=n)
    print("# Fields set in configuration\n", file=sio)
    format_counters(sio, [agg["fields_set"]], total_count=n)


def format_value_sets(sio, sr: ScanResult):
    vsc = sr.value_set_counters
    t = {"show_other_values": False, "top_table_minimum_count": 2, "show_unset_as_value": True}
    for heading, field, opts in [
        ("Top select sets", "select", t),
        ("Top extend-select sets", "extend_select", t),
        ("Top ignore sets", "ignore", t),
        ("Top extend-ignore sets", "extend_ignore", t),
        ("Top fixable sets", "fixable", t),
        ("Top unfixable sets", "unfixable", t),
        ("Top configuration field sets", "fields_set", {"show_other_values": False, "top_table_count": 10}),
    ]:
        print(f"# {heading}\n", file=sio)
        format_counters(sio, [vsc[field]], **opts)
