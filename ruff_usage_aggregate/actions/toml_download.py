from __future__ import annotations

import re

import diskcache
import httpx


def convert_github_url_to_raw_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("https://github.com/") and "/blob/" in url:
        return re.sub(
            r"^https://github.com/(.*)/blob/(.*)$",
            r"https://raw.githubusercontent.com/\1/\2",
            url,
        )
    if url.startswith("https://raw.githubusercontent.com/"):
        return url
    return None


def scan_cache_for_download_urls(cache: diskcache.Cache):
    """
    Find GitHub blob download URLs for TOML files from the cache.
    """
    for key in cache.iterkeys():
        if key.startswith("scan_github:"):
            data = cache[key]
            for item in data["items"]:
                download_url = convert_github_url_to_raw_url(
                    item.get("download_url") or item.get("html_url"),
                )
                if not download_url:
                    print(f"Unknown item: {item}")
                    continue
                yield download_url


def maybe_download_url(client: httpx.Client, cache: diskcache.Cache, url: str):
    # Remove fragment from URL first...
    url, _, _ = url.partition("#")
    if not url.endswith(".toml"):
        return
    cache_key = f"toml:{url}"
    if cache_key in cache:
        return
    print(f"Fetching {url}")
    resp = client.get(url)
    resp.raise_for_status()
    cache[cache_key] = resp.content.decode("utf-8")


def download_tomls_from_cache(cache: diskcache.Cache):
    """
    Download TOML files that have yet to be downloaded.
    """
    with httpx.Client() as client:
        for url in scan_cache_for_download_urls(cache):
            maybe_download_url(client, cache, url)


def download_tomls_from_file(cache: diskcache.Cache, file):
    """
    Download TOML files that have yet to be downloaded.
    """
    with httpx.Client() as client:
        for line in file:
            line = line.strip()
            url = convert_github_url_to_raw_url(line)
            if not url:
                continue
            maybe_download_url(client, cache, url)
