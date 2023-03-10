import argparse
import json
import sys
from functools import partial
from multiprocessing.pool import ThreadPool

import httpx
import tqdm

filename_guesses = ["pyproject.toml", "ruff.toml"]
branch_guesses = ["main", "master"]


def check(client, owner_and_repo) -> str:
    owner, repo = owner_and_repo.split("/", 1)
    for filename in filename_guesses:
        for ref in branch_guesses:
            url = f"https://raw.githubusercontent.com/{owner_and_repo}/{ref}/{filename}"
            resp = client.get(url)
            # print(url, resp.status_code, file=sys.stderr)
            if resp.status_code == 200 and b"ruff" in resp.content:
                datum = {
                    "owner": owner,
                    "repo": repo,
                    "path": filename,
                    "ref": ref,
                }
                return json.dumps(datum, sort_keys=True)
    return json.dumps({"owner": owner, "repo": repo, "error": "path-unknown"}, sort_keys=True)


def filter_work(ignored_repos):
    for line in tqdm.tqdm(sorted(set(sys.stdin))):
        owner_and_repo = line.strip()
        if owner_and_repo.lower() in ignored_repos:
            print("We already know:", owner_and_repo, file=sys.stderr)
            continue
        yield owner_and_repo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--known-jsonl", nargs="*")
    args = ap.parse_args()
    ignored_repos = set()
    ignored_docs = []
    for filename in args.known_jsonl or ():
        with open(filename) as f:
            ignored_docs.extend(json.loads(line.strip()) for line in f)
    ignored_repos.update({f"{i['owner']}/{i['repo']}".lower() for i in ignored_docs})
    print("Ignored repos:", len(ignored_repos), file=sys.stderr)
    with httpx.Client() as client:
        client.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RUA"
        work = list(filter_work(ignored_repos))
        with ThreadPool(4) as pool:
            check_p = partial(check, client)
            for result in tqdm.tqdm(pool.imap(check_p, work), total=len(work)):
                print(result, flush=True)


if __name__ == "__main__":
    main()
