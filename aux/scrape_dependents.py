import sys

import bs4
import httpx


def main():
    with httpx.Client() as c:
        c.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RUA"
        url = "https://github.com/charliermarsh/ruff/network/dependents?dependent_type=REPOSITORY"
        while True:
            print(url, file=sys.stderr)
            resp = c.get(url)
            if resp.status_code == 429:
                print("Got 429, stopping.", file=sys.stderr)
                break
            resp.raise_for_status()
            soup = bs4.BeautifulSoup(resp.content, "html.parser")
            repo_hrefs = [a["href"].lstrip("/") for a in soup.find_all("a", **{"data-hovercard-type": "repository"})]
            for repo_href in repo_hrefs:
                print(repo_href)
            sys.stdout.flush()
            next_link = soup.find("a", rel="nofollow", string="Next")
            if not next_link:
                break
            url = next_link["href"]


if __name__ == "__main__":
    main()
