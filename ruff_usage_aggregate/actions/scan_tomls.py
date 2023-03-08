import logging
import tomllib

import diskcache

from ruff_usage_aggregate.models import RuffConfig, ScanResult

log = logging.getLogger(__name__)


def get_downloaded_tomls(cache: diskcache.Cache):
    """
    Iterate over (URL, content) tuples for downloaded TOML files.
    """
    for key in cache.iterkeys():
        if key.startswith("toml:"):
            _, _, url = key.partition(":")
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
        ruff_section = toml.get("tool", {}).get("ruff")
        if not isinstance(ruff_section, dict):
            continue
        sr.configs.append(RuffConfig.from_toml_section(url=url, ruff_section=ruff_section))
    return sr
