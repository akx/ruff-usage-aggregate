from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import TextIO

import click

log = logging.getLogger(__name__)


@click.group()
@click.option("--github-token")
@click.option("--debug/--no-debug")
@click.pass_context
def main(context: click.Context, github_token: str | None, debug: bool):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    context.obj = {
        "github_token": github_token,
    }


@main.command()
@click.pass_context
@click.option("--output-jsonl", "-o", type=click.File("a"))
def scan_github_search(context: click.Context, output_jsonl: TextIO | None):
    """
    Scan GitHub Code Search for Ruff usage; output a JSONL file of raw search results.
    """
    github_token = context.obj["github_token"]
    if not github_token:
        raise ValueError("github_token is required")
    from ruff_usage_aggregate.actions.github_search import scan_github_search

    if not output_jsonl:
        filename = f"github_search_{int(time.time())}.jsonl"
        print(f"Writing to {filename}")
        output_jsonl = open(filename, "a")

    for datum in scan_github_search(github_token=github_token):
        print(json.dumps(datum), file=output_jsonl)


@main.command()
@click.argument("input_files", nargs=-1, type=click.File("r"))
def combine(input_files: list[TextIO]):
    """
    Combine "known tomls" data.
    """
    data = []
    for input_file in input_files:
        if input_file.name.endswith(".csv"):
            csv_data = list(csv.DictReader(input_file))
            log.info(f"{input_file.name}: read {len(csv_data)} entries")
            data.extend(csv_data)
        elif input_file.name.endswith(".jsonl"):
            jsonl_data = []
            for line in input_file:
                line = json.loads(line)
                if line.get("total_count") and line.get("items"):  # smells like a GitHub Search line
                    for item in line["items"]:
                        jsonl_data.append(
                            {
                                "owner": item["repository"]["owner"]["login"],
                                "repo": item["repository"]["name"],
                                "path": item["path"],
                            },
                        )
                elif all(k in line for k in ("owner", "repo", "path")):
                    jsonl_data.append(line)
                else:
                    log.warning(f"Unknown JSONL line: {line}")
            log.info(f"{input_file.name}: read {len(jsonl_data)} entries")
            data.extend(jsonl_data)
    last_line = None
    n = 0
    for datum in sorted(data, key=lambda d: (d["owner"], d["repo"], d["path"])):
        line = json.dumps(datum, sort_keys=True, ensure_ascii=False)
        if line != last_line:
            print(line)
            n += 1
            last_line = line

    log.info(f"Wrote {n} unique entries")


@main.command()
@click.pass_context
@click.option("--output-directory", "-o", type=click.Path(dir_okay=True, file_okay=False))
def download_tomls(
    context: click.Context,
    output_directory: str | None,
):
    """
    Download TOMLs from a known TOMLs JSONL (from stdin).
    """
    from ruff_usage_aggregate.actions.toml_download import download_tomls

    if not output_directory:
        output_directory = f"./tomls_{int(time.time())}"
        print(f"Writing to {output_directory}")

    os.makedirs(output_directory, exist_ok=True)

    download_tomls(
        output_directory=Path(output_directory),
        data=[json.loads(line) for line in sys.stdin],
        github_token=context.obj["github_token"],
    )


@main.command()
@click.option("--input-directory", "-i", type=click.Path(dir_okay=True, file_okay=False, exists=True))
@click.option("--output-format", "-o", type=click.Choice(["json", "top-markdown"]), required=True)
def scan_tomls(input_directory: str, output_format: str):
    """
    Scan downloaded TOML files for Ruff usage.
    """
    from ruff_usage_aggregate.actions.scan_tomls import scan_tomls

    sr = scan_tomls(input_directory=Path(input_directory))
    if output_format == "json":
        sorted_value_sets = {
            key: [(sorted(c_key), value) for c_key, value in counter.most_common()]
            for key, counter in sr.get_value_set_counters().items()
        }
        jsonable = {
            "aggregate": sr.aggregate(),
            "value_sets": sorted_value_sets,
        }
        print(json.dumps(jsonable, indent=2))
    elif output_format == "top-markdown":
        from ruff_usage_aggregate.format.top_markdown import format_top_markdown

        print(format_top_markdown(sr))
