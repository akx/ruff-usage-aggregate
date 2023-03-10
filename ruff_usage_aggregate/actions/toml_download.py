from __future__ import annotations

import logging
import re
from multiprocessing.pool import ThreadPool
from pathlib import Path

import httpx
import tqdm

log = logging.getLogger(__name__)


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


def download_tomls(
    output_directory: Path,
    data: list[dict],
    github_token: str | None = None,
):
    def _do_download(datum: dict):
        if "error" in datum:
            return
        if "owner" in datum and "repo" in datum and "path" in datum:
            download_from_github_datum(
                client=client,
                output_directory=output_directory,
                datum=datum,
                github_token=github_token,
            )
        else:
            print("Skipping:", datum)

    with httpx.Client() as client:
        with ThreadPool(5) as pool:
            for _ in tqdm.tqdm(pool.imap_unordered(_do_download, data), total=len(data)):
                pass


def download_from_github_datum(
    client: httpx.Client,
    output_directory: Path,
    datum: dict,
    github_token: str | None = None,
):
    repo = f"{datum['owner']}/{datum['repo']}"
    storage_filename = output_directory / f"github/{repo}/{datum['path']}".replace("/", "#")
    if storage_filename.exists():
        log.debug("Already got: %s", storage_filename)
        return
    if datum.get("ref"):
        url = f"https://raw.githubusercontent.com/{repo}/{datum['ref']}/{datum['path']}"
        resp = client.get(url)
    else:
        url = f"https://api.github.com/repos/{repo}/contents/{datum['path']}"
        headers = {"Accept": "application/vnd.github.raw"}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"
        resp = client.get(url, headers=headers)
    if resp.status_code == 404:
        log.warning("Got 404 for %s (URL %s)", datum, url)
        return
    if resp.status_code == 200:
        storage_filename.write_bytes(resp.content)
        log.info("Downloaded: %s from %s", datum, url)
    resp.raise_for_status()
