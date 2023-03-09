import csv
import json
import logging
import sys

import click
import diskcache


@click.group()
@click.option("--github-token")
@click.option("--cache-dir", default="./.cache", type=click.Path(dir_okay=True, file_okay=False))
@click.option("--debug/--no-debug")
@click.pass_context
def main(context: click.Context, github_token: str | None, cache_dir: str, debug: bool):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    context.obj = {
        "cache": diskcache.Cache(
            cache_dir,
            size_limit=sys.maxsize,
            disk_min_file_size=1048576,
            eviction_policy="none",
        ),
        "github_token": github_token,
    }


@main.command()
@click.pass_context
def scan_github_search(context: click.Context):
    """
    Scan GitHub Code Search for Ruff-ish TOML file URLs.
    """
    github_token = context.obj["github_token"]
    if not github_token:
        raise ValueError("github_token is required")
    from ruff_usage_aggregate.actions.github_search import scan_github_search

    scan_github_search(cache=context.obj["cache"], github_token=github_token)


@main.command()
@click.pass_context
def download_tomls_from_cache(context: click.Context):
    """
    Download TOMLs for URLs gathered by scan_github_search.
    """
    from ruff_usage_aggregate.actions.toml_download import download_tomls_from_cache

    download_tomls_from_cache(context.obj["cache"])


@main.command()
@click.pass_context
def download_tomls_from_file(context: click.Context):
    """
    Download TOMLs from URLs given as standard input.
    """
    from ruff_usage_aggregate.actions.toml_download import download_tomls_from_file

    download_tomls_from_file(context.obj["cache"], sys.stdin)


@main.command()
@click.option("--output-format", "-o", type=click.Choice(["json", "top-markdown"]), required=True)
@click.pass_context
def scan_tomls(context: click.Context, output_format: str):
    """
    Scan downloaded TOML files for Ruff usage.
    """
    from ruff_usage_aggregate.actions.scan_tomls import scan_tomls

    sr = scan_tomls(context.obj["cache"])
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


@main.command()
@click.pass_context
def dump_downloaded_tomls(context: click.Context):
    """
    Dump downloaded TOMLs as JSON.
    """
    from ruff_usage_aggregate.actions.scan_tomls import get_downloaded_tomls

    print(json.dumps(dict(get_downloaded_tomls(context.obj["cache"]))))


@main.command()
@click.pass_context
def dump_downloaded_toml_github_csv(context: click.Context):
    """
    Dump owner/repo/path of downloaded and validated TOMLs as CSV.
    """
    from ruff_usage_aggregate.actions.scan_tomls import get_valid_tomls_github_owner_repo_path

    cache = context.obj["cache"]
    cw = csv.writer(sys.stdout)
    cw.writerow(["owner", "repo", "path"])
    for owner, repo, path in sorted(get_valid_tomls_github_owner_repo_path(cache)):
        cw.writerow([owner, repo, path])
