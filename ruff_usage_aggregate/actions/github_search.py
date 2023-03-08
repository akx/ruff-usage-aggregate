import random
import time

import diskcache
import httpx

from ruff_usage_aggregate.helpers import sleep_with_progress


def scan_github_search(
    *,
    cache: diskcache.Cache,
    github_token: str,
    min_page: int = 1,
    max_page: int = 20,
    shuffle: bool = False,
):
    # This does seem to quickly end up in a rate-limiting limbo (at around page 11 for me).
    timestamp = int(time.time())
    pages = list(range(min_page, max_page + 1))
    if shuffle:
        random.shuffle(pages)
    with httpx.Client() as client:
        for page in pages:
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
            cache_key = f"scan_github:{timestamp}:{page}"
            cache[cache_key] = data
            if not data.get("items"):
                break
