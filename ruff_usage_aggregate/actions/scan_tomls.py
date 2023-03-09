import logging
import sys
import tomllib
from urllib.parse import unquote

import diskcache

from ruff_usage_aggregate.errors import NotRuffyError
from ruff_usage_aggregate.models import RuffConfig, ScanResult

log = logging.getLogger(__name__)


def get_downloaded_toml_urls(cache: diskcache.Cache):
    """
    Iterate over URLs and cache keys for downloaded TOML files.
    """
    for key in cache.iterkeys():
        if key.startswith("toml:"):
            _, _, url = key.partition(":")
            yield (url, key)


def get_downloaded_tomls(cache: diskcache.Cache):
    """
    Iterate over (URL, content) tuples for downloaded TOML files.
    """
    for url, key in get_downloaded_toml_urls(cache):
        try:
            toml = tomllib.loads(cache[key])
        except Exception as e:
            log.error(f"Error parsing {url}: {e}")
            continue
        if not isinstance(toml, dict):
            log.warning(f"Unexpected TOML type for {url}: {type(toml)}")
            continue
        yield (url, toml)


def scan_tomls(cache: diskcache.Cache) -> ScanResult:
    sr = ScanResult()
    for url, toml in get_downloaded_tomls(cache):
        if url.endswith("ruff.toml"):
            # for a ruff.toml, the whole shebang is the config
            ruff_section = toml
        else:  # otherwise assume pyproject.toml
            ruff_section = toml.get("tool", {}).get("ruff")
        if not isinstance(ruff_section, dict):
            continue
        if not ruff_section:
            continue
        try:
            rc = RuffConfig.from_toml_section(url=url, ruff_section=ruff_section)
        except NotRuffyError:
            log.exception(f"Not ruffy: {url}")
            continue
        sr.configs.append(rc)
    return sr


def get_valid_tomls_github_owner_repo_path(cache: diskcache.Cache):
    knowledge = set()

    for rc in scan_tomls(cache).configs:
        url = rc.url
        if url.startswith("https://raw.githubusercontent.com/"):
            _, _, rest = url.partition("https://raw.githubusercontent.com/")
            owner, _, rest = rest.partition("/")
            repo, _, rest = rest.partition("/")
            ref, _, path = rest.partition("/")
            knowledge.add((owner, repo, unquote(path)))
        elif url.startswith("~"):
            owner, repo, ref, path = url[1:].split("/", 3)
            knowledge.add((owner, repo, unquote(path)))
        else:
            print(f"Unknown URL: {url}", file=sys.stderr)
    return knowledge
