"""Removes forks, missing repositories and repositories without a path to create a
clean dataset to use with ecosystem checks"""

import asyncio
import dataclasses
import json
import logging
from asyncio import Semaphore
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from httpx import AsyncClient, HTTPError
from tqdm import tqdm

from ruff_usage_aggregate.helpers.jsonl import read_jsonl, write_jsonl

logger = logging.getLogger(__name__)


# https://stackoverflow.com/a/71666789/3549270
class RepoStatus(str, Enum):
    FORK = "fork"
    REPO = "repo"
    ERROR = "error"


@dataclass
class RepoInfo:
    owner: str
    repo: str
    path: str
    ref: Optional[str]
    status: RepoStatus


async def query_github(owner: str, repo: str, path: str, client: AsyncClient, github_token: str) -> RepoInfo:
    # E.g. https://api.github.com/repos/Hadryan/OpenBBTerminal
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RUA",
    }
    response = await client.get(url, headers=headers, follow_redirects=True)
    # GitHub also returns 404 for private repositories
    if response.status_code == 404:
        return RepoInfo(owner, repo, path, None, RepoStatus.ERROR)
    response.raise_for_status()
    data = response.json()
    if data["fork"]:
        repo_status = RepoStatus.FORK
    else:
        repo_status = RepoStatus.REPO
    return RepoInfo(owner, repo, path, data["ref"], repo_status)


async def query_github_slow(
    owner: str, repo: str, path: str, client: AsyncClient, github_token: str, slow_down: Semaphore
) -> RepoInfo | tuple[str, str, HTTPError]:
    # There is an actual ratelimit with github (5000 requests per hour), but we still want 3k parallel requests,
    # so we slow it down to 50 (see below) at the same time here
    async with slow_down:
        try:
            return await query_github(owner, repo, path, client, github_token)
        except HTTPError as e:
            # Don't lose the error source across as_completed
            return owner, repo, e


async def clean_with_repo_api_async(
    known_github_tomls: Path, known_github_tomls_no_forks: Path, repo_api_data: Path, github_token: str
):
    repos = list(read_jsonl(known_github_tomls))
    paths = {}
    for repo in repos:
        if path := repo.get("path"):
            paths[(repo["owner"], repo["repo"])] = path
    known_info: dict[(str, str), RepoInfo] = {}
    for entry in read_jsonl(repo_api_data):
        if path := paths[(entry["owner"], entry["repo"])]:
            known_info[(entry["owner"], entry["repo"])] = RepoInfo(path=path, **entry)

    with repo_api_data.open("a") as is_fork_fp:
        async with AsyncClient() as client:
            slow_down = Semaphore(50)
            tasks = []
            for repo in repos:
                if (repo["owner"], repo["repo"]) not in known_info:
                    tasks.append(
                        asyncio.create_task(
                            query_github_slow(
                                repo["owner"], repo["repo"], repo["path"], client, github_token, slow_down
                            )
                        )
                    )
            for completed in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
                repo_info = await completed
                if isinstance(repo_info, RepoInfo):
                    # Write them here already so it survives in case of crash
                    is_fork_fp.write(json.dumps(dataclasses.asdict(repo_info)) + "\n")
                    known_info[(repo_info.owner, repo_info.repo)] = repo_info
                else:
                    logger.error(f"Failed to query {repo_info[0]}/{repo_info[1]}: {repo_info[2]}")

    repos_no_forks = []
    for repo in repos:
        if repo_info := known_info.get((repo["owner"], repo["repo"])):
            if repo_info.status == RepoStatus.REPO:
                repos_no_forks.append(dataclasses.asdict(repo_info))

    print(f"{len(repos_no_forks)} of {len(repos)} repositories are not forks")
    write_jsonl(known_github_tomls_no_forks, repos_no_forks)
