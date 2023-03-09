import logging
import time
from collections.abc import Iterable

import httpx

from ruff_usage_aggregate.helpers import sleep_with_progress

log = logging.getLogger(__name__)


def scan_github_search(
    *,
    github_token: str,
) -> Iterable[dict]:
    with httpx.Client() as client:
        for page in range(1, 11):
            while True:
                print(f"Fetching page {page}")
                resp = client.get(
                    "https://api.github.com/search/code",
                    params={
                        "q": "ruff in:file extension:toml",
                        "per_page": 100,
                        "page": page,
                        "sort": "indexed",
                        "order": "desc",
                    },
                    headers={
                        "Accept": "application/vnd.github.v3+json",
                        "Authorization": f"Bearer {github_token}",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                if resp.status_code in (403, 422):
                    sleep_time = 10
                    if "x-ratelimit-reset" in resp.headers:
                        reset = int(resp.headers["x-ratelimit-reset"])
                        now = int(time.time())
                        if reset > now:
                            sleep_time = (reset - now) + 5  # Add some time to be safe
                    sleep_with_progress(sleep_time, "Rate limited")
                    continue
                break
            if resp.status_code != 200:
                print(resp.headers)
                print(resp.content)
                print(resp.status_code)
                resp.raise_for_status()
            data = resp.json()
            yield data
            if not data.get("items"):
                log.info("Ran out of items.")
                break
