#!/usr/bin/env python3
"""Generate GitHub profile README with PR contribution stats."""

import os
import sys
from datetime import datetime
from collections import defaultdict

import requests

GITHUB_API = "https://api.github.com"


def get_username():
    return sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_USERNAME", "")


def github_get(path, token=None, params=None):
    """Make authenticated GitHub API request."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"{GITHUB_API}/{path}"
    resp = requests.get(url, headers=headers, params=params or {})
    resp.raise_for_status()
    return resp.json()


def get_user_prs(username, token=None, max_pages=20):
    """Get all PRs authored by the user across all repos."""
    prs = []
    page = 1
    per_page = 100

    while page <= max_pages:
        data = github_get(
            f"search/issues",
            token=token,
            params={
                "q": f"type:pr author:{username}",
                "sort": "created",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
        )
        items = data.get("items", [])
        if not items:
            break
        prs.extend(items)
        if len(prs) >= data["total_count"]:
            break
        page += 1

    return prs


def get_user_repos(username, token=None):
    """Get repos owned by the user."""
    repos = []
    page = 1
    while True:
        data = github_get(
            f"users/{username}/repos",
            token=token,
            params={"type": "owner", "sort": "created", "per_page": 100, "page": page},
        )
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def build_readme(username, token):
    """Build the full README content."""
    now = datetime.now()

    # 1. Get owned repos
    print(f"Fetching repos owned by {username}...")
    owned_repos = get_user_repos(username, token)

    # 2. Get all PRs
    print(f"Fetching PRs by {username}...")
    prs = get_user_prs(username, token)

    # 3. Build owned repos table
    print("Building owned repos table...")
    owned_table = []
    total_stars = 0
    for i, repo in enumerate(owned_repos, 1):
        name = repo["full_name"]
        created = repo["created_at"][:10]
        updated = repo["pushed_at"][:10] if repo.get("pushed_at") else repo["updated_at"][:10]
        lang = repo.get("language") or ""
        stars = repo.get("stargazers_count", 0)
        total_stars += stars
        url = repo["html_url"]
        owned_table.append(
            f"| {i} | [{name}]({url}) | {created} | {updated} | {lang} | {stars} |"
        )
    owned_table.append(f"| sum | | | | | {total_stars} |")

    # 4. Build contribution table grouped by repo
    print("Building contribution table...")
    repo_stats = defaultdict(lambda: {"count": 0, "first": None, "last": None})
    for pr in prs:
        # repo_url from the URL: https://github.com/owner/repo/pull/123
        repo_url = pr.get("repository_url", "")
        if not repo_url:
            continue
        # Extract owner/repo
        parts = repo_url.split("/")[-2:]
        repo_name = "/".join(parts)
        created = pr.get("created_at", "")[:10]
        html_url = pr.get("html_url", "")

        stats = repo_stats[repo_name]
        stats["count"] += 1
        if stats["first"] is None or created < stats["first"]:
            stats["first"] = created
        if stats["last"] is None or created > stats["last"]:
            stats["last"] = created
        # Keep the last PR URL
        stats["url"] = html_url

    # Sort by PR count descending
    sorted_repos = sorted(repo_stats.items(), key=lambda x: x[1]["count"], reverse=True)

    contrib_table = []
    for i, (repo, stats) in enumerate(sorted_repos, 1):
        repo_url = f"https://github.com/{repo}"
        first_link = f"[{stats['first']}](https://github.com/{repo}/pulls?q=is%3Apr+author%3A{username}+is%3Aclosed+sort%3Acreated-asc)"
        last_link = f"[{stats['last']}](https://github.com/{repo}/pulls?q=is%3Apr+author%3A{username}+is%3Aclosed+sort%3Acreated-desc)"
        pr_count = f"[{stats['count']}](https://github.com/{repo}/pulls?q=is%3Apr+author%3A{username})"
        contrib_table.append(
            f"| {i} | [{repo}]({repo_url}) | {first_link} | {last_link} | {pr_count} |"
        )

    # 5. Assemble README
    owned_header = "| ID  | REPO | START | UPDATE | LANGUAGE | STARS |"
    owned_sep = "|-----|------|-------|--------|----------|-------|"
    owned_body = "\n".join(owned_table)

    contrib_header = "| ID  | REPO | FIRSTDATE | LASTEDATE | PRCOUNT |"
    contrib_sep = "|-----|------|-----------|-----------|---------|"
    contrib_body = "\n".join(contrib_table)

    nl = "\n"
    readme = (
        f"## Hi 👋"
        f"\n\n"
        f"**因上努力，果上随缘** ."
        f"\n\n"
        f"**From github: [{username}](https://github.com/{username})** ."
        f"\n\n"
        f"<!--START_SECTION:my_github-->"
        f"\n## The repos I created"
        f"\n{owned_header}"
        f"\n{owned_sep}"
        f"\n{owned_body}"
        f"\n\n## The repos I contributed to"
        f"\n{contrib_header}"
        f"\n{contrib_sep}"
        f"\n{contrib_body}"
        f"\n<!--END_SECTION:my_github-->"
        f"\n\n"
        f"*Last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}*"
        f"\n"
    )
    return readme


def main():
    username = get_username()
    if not username:
        print("Error: GitHub username is required")
        sys.exit(1)

    token = os.environ.get("GITHUB_TOKEN", "")

    print(f"Generating README for {username}...")
    readme = build_readme(username, token)

    # Write to README.md
    readme_path = os.path.join(os.environ.get("GITHUB_WORKSPACE", "."), "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"README written to {readme_path}")
    print("Done!")


if __name__ == "__main__":
    main()
