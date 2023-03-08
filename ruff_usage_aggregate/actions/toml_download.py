from __future__ import annotations

import base64
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


def download_tomls_from_known_repos(cache: diskcache.Cache):
    from ruff_usage_aggregate.data.known_repos import known_repos
    with httpx.Client() as client:
        for repo in known_repos:
            for url in [
                f"https://api.github.com/repos/{repo}/contents/pyproject.toml",
                f"https://api.github.com/repos/{repo}/contents/ruff.toml",
            ]:
                _process_github_contents_url(cache, client, url, repo)


def _process_github_contents_url(cache, client, content_url, repo):
    resp = client.get(content_url)
    if resp.status_code == 404:
        print("404", content_url)
        return
    resp.raise_for_status()
    data = resp.json()
    # pseudo-URL for cache key because the contents/ API
    # doesn't resolve the ref name to a canonical commit SHA
    url = f"~{repo}/{data['sha']}/pyproject.toml"
    cache_key = f"toml:{url}"
    if cache_key in cache:
        return
    if data.get("content"):
        if data["encoding"] != "base64":
            raise ValueError(f"Unknown encoding: {data['encoding']}")
        content = base64.b64decode(data["content"]).decode("utf-8")
        cache[cache_key] = content
        print("Got:", cache_key)
    else:
        print("No content...", content_url, data)
