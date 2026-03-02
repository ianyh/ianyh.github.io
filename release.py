#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

REPO = "ianyh/Amethyst"
SITE_BASE_URL = "https://ianyh.com/amethyst/versions"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a new release of Amethyst.")
    parser.add_argument("--version", required=True, help="Version string, e.g. 0.24.1 (suffix with b for canary-only, e.g. 0.24.1b)")
    parser.add_argument("--build", required=True, help="Sparkle build number (CFBundleVersion), e.g. 125")
    parser.add_argument("--min-os", default="11.0.0", help="Minimum macOS version (default: 11.0.0)")
    parser.add_argument("--channel", choices=["prod", "canary", "both"], help="Which appcast(s) to update (default: canary for beta versions, both for stable)")
    return parser.parse_args()


def format_pub_date(iso_date):
    d = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    return d.strftime("%a, %d %b %Y 00:00:00 +0000")


def fetch_release(tag):
    print(f"Fetching release info for {tag}...")
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{REPO}/releases/tags/{tag}"],
            capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        print("Failed to fetch release from GitHub API.", file=sys.stderr)
        print("Make sure `gh` is installed and authenticated.", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("`gh` not found. Install it with: brew install gh", file=sys.stderr)
        sys.exit(1)


def fetch_release_notes(tag, notes_file):
    print(f"Fetching release notes → {os.path.relpath(notes_file, SCRIPT_DIR)}")
    release_url = f"https://github.com/{REPO}/releases/tag/{tag}"
    response = requests.get(release_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    with open(notes_file, "w") as f:
        title = soup.select_one("div.Box-body div:not(.markdown-body) h1")
        if title:
            f.write(str(title) + "\n")
        body = soup.select_one("div.markdown-body")
        if body:
            f.write(str(body) + "\n")


def build_item(short_version, build_number, pub_date, min_os, version, file_size, tag):
    download_url = f"https://github.com/{REPO}/releases/download/{tag}/Amethyst.zip"
    release_notes_url = f"{SITE_BASE_URL}/Amethyst-{version}.html"
    return (
        f"\t\t<item>\n"
        f"\t\t\t<title>Version {short_version}</title>\n"
        f"\t\t\t<description></description>\n"
        f"\t\t\t<pubDate>{pub_date}</pubDate>\n"
        f"\t\t\t<sparkle:minimumSystemVersion>{min_os}</sparkle:minimumSystemVersion>\n"
        f"\t\t\t<sparkle:releaseNotesLink>{release_notes_url}</sparkle:releaseNotesLink>\n"
        f"\t\t\t<enclosure url=\"{download_url}\"\n"
        f"\t\t\t\tsparkle:version=\"{build_number}\"\n"
        f"\t\t\t\tsparkle:shortVersionString=\"{short_version}\"\n"
        f"\t\t\t\tlength=\"{file_size}\"\n"
        f"\t\t\t\ttype=\"application/octet-stream\"\n"
        f"\t\t\t\t/>\n"
        f"\t\t</item>"
    )


def add_to_appcast(appcast_path, item):
    with open(appcast_path) as f:
        content = f.read()
    marker = "\t</channel>"
    idx = content.rfind(marker)
    if idx == -1:
        print(f"Could not find insertion point in {appcast_path}", file=sys.stderr)
        sys.exit(1)
    updated = content[:idx] + item + "\n" + content[idx:]
    with open(appcast_path, "w") as f:
        f.write(updated)
    print(f"  Updated {os.path.relpath(appcast_path, SCRIPT_DIR)}")


def main():
    args = parse_args()

    version = args.version
    build_number = args.build
    min_os = args.min_os
    is_canary = version.endswith("b")
    short_version = version[:-1] if is_canary else version
    channel = args.channel or ("canary" if is_canary else "both")
    tag = f"v{version}"

    print(f"Generating Amethyst {version} (build {build_number}) → channel: {channel}")
    print()

    release = fetch_release(tag)

    pub_date = format_pub_date(release["published_at"])
    asset = next((a for a in release["assets"] if a["name"] == "Amethyst.zip"), None)
    if asset is None:
        print("Could not find Amethyst.zip in the release assets.", file=sys.stderr)
        sys.exit(1)
    file_size = asset["size"]

    print(f"  Date:      {pub_date}")
    print(f"  File size: {file_size} bytes")
    print()

    notes_file = os.path.join(SCRIPT_DIR, f"source/amethyst/versions/Amethyst-{version}.html")
    fetch_release_notes(tag, notes_file)
    print()

    item = build_item(short_version, build_number, pub_date, min_os, version, file_size, tag)

    print("Updating appcasts...")
    if channel in ("canary", "both"):
        add_to_appcast(os.path.join(SCRIPT_DIR, "source/amethyst/canary-appcast.xml"), item)
    if channel in ("prod", "both"):
        add_to_appcast(os.path.join(SCRIPT_DIR, "source/amethyst/appcast.xml"), item)
    print()

    print("Building site...")
    subprocess.run(["node", "build.js"], cwd=SCRIPT_DIR, check=True)
    subprocess.run(["cp", "-r", "build/", "deploy/"], cwd=SCRIPT_DIR, check=True)

    print()
    print(f"Done! Amethyst {version} generated.")


if __name__ == "__main__":
    main()
