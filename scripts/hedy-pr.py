#!/usr/bin/env python3
"""Pull request helper for Hedy's post pipeline (see EDITORIAL_POLICY.md).

Usage:
  python3 scripts/hedy-pr.py pending
      Prints "PENDIENTE: #<n> <title> <url>" for each open PR from a post/* branch,
      or "NINGUNO" if there are none.
  python3 scripts/hedy-pr.py open <branch> <title> <body-file>
      Opens a PR from <branch> into main and prints "PR_URL=<url>".

It intentionally has no merge command: only Abimelek merges, from GitHub.
The token is read from the git remote URL of this repo.
"""

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "abimelekcastrezana/hedy-diario"
API = f"https://api.github.com/repos/{REPO}"


def token():
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True
    ).stdout.strip()
    match = re.match(r"https://[^:/]+:([^@]+)@github\.com/", url)
    if not match:
        sys.exit("ERROR: no encontré el token en el remote 'origin'")
    return match.group(1)


def request(method, path, data=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Authorization": f"Bearer {token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: GitHub respondió {e.code}: {e.read().decode(errors='replace')}")


def pending():
    prs = [p for p in request("GET", "/pulls?state=open&base=main&per_page=100")
           if p["head"]["ref"].startswith("post/")]
    if not prs:
        print("NINGUNO")
    for p in prs:
        print(f"PENDIENTE: #{p['number']} {p['title']} {p['html_url']}")


def open_pr(branch, title, body_file):
    if not branch.startswith("post/"):
        sys.exit("ERROR: la rama debe empezar con post/")
    with open(body_file, encoding="utf-8") as f:
        body = f.read()
    pr = request("POST", "/pulls", {"title": title, "head": branch, "base": "main", "body": body})
    print(f"PR_URL={pr['html_url']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["pending"]:
        pending()
    elif len(args) == 4 and args[0] == "open":
        open_pr(*args[1:])
    else:
        sys.exit(__doc__)
