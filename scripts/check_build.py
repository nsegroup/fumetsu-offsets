#!/usr/bin/env python3
"""Return the current CS2 public build id, and whether it differs from what we
last published (offsets/latest.json). Exit 0 and print NEW=<build> when a fresh
dump is needed; print NEW= (empty) when unchanged so the workflow can skip.

Build id source: the public SteamCMD info mirror (api.steamcmd.net), which
exposes app 730's public-branch buildid without any login. No game, no account.
"""
import json, os, sys, urllib.request

APP = "730"
LATEST = os.path.join(os.path.dirname(__file__), "..", "offsets", "latest.json")


def current_buildid() -> str:
    url = f"https://api.steamcmd.net/v1/info/{APP}"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    depots = data["data"][APP]["depots"]
    return str(depots["branches"]["public"]["buildid"])


def published_buildid() -> str:
    try:
        with open(LATEST, encoding="utf-8") as f:
            env = json.load(f)
        # envelope carries the steam buildid it was produced from
        return str(env.get("steam_buildid", ""))
    except (OSError, ValueError):
        return ""


def main() -> int:
    cur = current_buildid()
    pub = published_buildid()
    out = os.environ.get("GITHUB_OUTPUT")
    new = cur if cur != pub else ""
    line_build = f"buildid={cur}"
    line_new = f"new={new}"
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(line_build + "\n" + line_new + "\n")
    print(f"current steam buildid: {cur}")
    print(f"last published:        {pub or '(none)'}")
    print("NEW DUMP NEEDED" if new else "up to date, skipping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
