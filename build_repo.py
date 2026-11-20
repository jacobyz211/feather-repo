#!/usr/bin/env python3
"""Build a merged Feather/AltStore repo from fastsign.dev and Moe's App Hub.

Sources:
  * https://fastsign.dev/repo.json   (full AltStore-format JSON, ~17k apps)
  * https://moe.mohkg1017.pro/        (HTML catalog, no repo JSON published)

Feather has to download, decode and import every app in this file, so the output is
written in a deliberately small shape: only fields Feather reads, one version per
app (upstream has exactly one anyway), duplicate icon/bundle/date keys dropped, long
descriptions clipped, and the whole file minified.

Run:  python build_repo.py
Out:  repo.json
"""

import html
import io
import json
import os
import re
import sys
import urllib.request

FASTSIGN = "https://fastsign.dev/repo.json"
MOE = "https://moe.mohkg1017.pro"
OUT = "repo.json"
MAX_DESC = 500

REPO_NAME = "Moe x FastSign"
REPO_IDENTIFIER = "pro.moe.fastsign"
REPO_SUBTITLE = "Moe's App Hub + Alan's Gigantic Repo, combined"
REPO_ICON = f"{MOE}/static/icons/icon-180x180.png"
# Set REPO_URL to the public URL where repo.json is hosted when building for release.
SOURCE_URL = os.environ.get("REPO_URL", "")

UA = {"User-Agent": "Mozilla/5.0 (compatible; feather-repo-builder/1.0)"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def google_drive_direct(url: str) -> str:
    """Turn Drive share links into direct download links where possible."""
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?(?:export=download&)?id=)([\w-]{10,})", url)
    if not m:
        return url
    return "https://drive.google.com/uc?export=download&id=%s&confirm=t" % m.group(1)


def size_to_bytes(num: str, unit: str) -> int:
    mult = {"KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}[unit]
    return int(float(num) * mult)


def parse_moe_cards(page: str):
    cards = []
    for art in page.split('<article class="app-card"')[1:]:
        art = art.split("</article>")[0]

        def attr(key):
            m = re.search(key + r'="([^"]*)"', art)
            return html.unescape(m.group(1)) if m else ""

        app_id = attr("data-app-id")
        if not app_id:
            continue

        desc_m = re.search(r'<p class="app-description[^"]*">(.*?)</p>', art, re.S)
        desc = html.unescape(re.sub(r"<[^>]+>", "", desc_m.group(1))).strip() if desc_m else ""

        size_m = re.search(r">\s*([\d.]+)\s*(KB|MB|GB)\s*<", art)

        cards.append({
            "id": app_id,
            "name": attr("data-app-name"),
            "version": attr("data-version"),
            "downloadURL": google_drive_direct(attr("data-download-url")),
            "bundleIdentifier": attr("data-bundle-id"),
            "iconURL": attr("data-icon-url"),
            "description": desc,
            "size": size_to_bytes(*size_m.groups()) if size_m else None,
            "date": attr("data-updated"),
        })
    return cards


def scrape_moe():
    apps = {}
    total = None
    stale = 0
    for page_no in range(1, 31):
        page = fetch(f"{MOE}/?page={page_no}").decode("utf-8", "replace")
        if total is None:
            m = re.search(r"of\s+(\d+)\s+apps", page)
            if m:
                total = int(m.group(1))
        before = len(apps)
        for card in parse_moe_cards(page):
            apps.setdefault(card["id"], card)
        if len(apps) == before:
            stale += 1
        else:
            stale = 0
        if total and len(apps) >= total:
            break
        # Pages overlap heavily; three pages with no new apps means we're done.
        if stale >= 3:
            break
    if total and len(apps) < total:
        print(f"warning: found {len(apps)} of {total} Moe apps", file=sys.stderr)
    return list(apps.values())


def moe_to_app(card):
    icon = card["iconURL"]
    if icon.startswith("/"):
        icon = MOE + icon
    name = card["name"].strip() or "Untitled"
    version = card["version"].strip() or "1.0"
    bundle = card["bundleIdentifier"].strip()
    if not bundle:
        # A handful of Moe entries don't declare a bundle ID. Fabricate a stable
        # reverse-DNS one so Feather keeps them distinct instead of grouping them.
        slug = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")[:40].strip(".")
        slug = re.sub(r"\.+", ".", slug)
        bundle = f"pro.moe.{slug}.{card['id'].rsplit('_', 1)[-1]}"

    desc = card["description"] or f"{name} for iOS (version {version}). Source: Moe's App Hub."
    entry = {
        "name": name,
        "bundleIdentifier": bundle,
        "developerName": "Moe",
        "version": version,
        "versionDate": card["date"] or "2026-01-01",
        "downloadURL": card["downloadURL"],
        "iconURL": icon,
        "localizedDescription": desc[:MAX_DESC],
        "type": 1,
    }
    if card["size"]:
        entry["size"] = card["size"]
    return entry


def slim_fastsign(app):
    """Reduce a fastsign entry to the fields Feather reads.

    The upstream entry repeats itself: `icon` == `iconURL`, `bundleID` ==
    `bundleIdentifier`, `fullDate` duplicates `versionDate`, and `versions` always
    holds exactly one copy of the same version. Dropping those cuts the file roughly
    in half without losing anything Feather displays.
    """
    dl = app.get("downloadURL")
    icon = app.get("iconURL")
    bundle = app.get("bundleIdentifier") or app.get("bundleID")
    if not dl or not icon or not bundle:
        return None

    entry = {
        "name": app.get("name") or "Untitled",
        "bundleIdentifier": bundle,
        "developerName": app.get("developerName") or "Unknown",
        "version": str(app.get("version") or "1.0"),
        "versionDate": app.get("versionDate") or app.get("date") or "2026-01-01",
        "downloadURL": dl,
        "iconURL": icon,
        "localizedDescription": (app.get("localizedDescription") or "")[:MAX_DESC],
        "type": 1,
    }
    if app.get("subtitle"):
        entry["subtitle"] = app["subtitle"]
    size = app.get("size")
    if size not in (None, ""):
        try:
            entry["size"] = int(size)
        except (TypeError, ValueError):
            pass
    if app.get("minOSVersion"):
        entry["minOSVersion"] = str(app["minOSVersion"])
    if app.get("tintColor"):
        entry["tintColor"] = app["tintColor"]
    return entry


def main():
    print("fetching fastsign...")
    fs = json.loads(fetch(FASTSIGN).decode("utf-8"))
    fs_apps = [a for a in (slim_fastsign(a) for a in fs["apps"]) if a]
    print(f"  {len(fs_apps)} apps")

    print("scraping moe...")
    moe_cards = scrape_moe()
    moe_apps = [moe_to_app(c) for c in moe_cards]
    print(f"  {len(moe_apps)} apps")

    # Moe names collide with a few fastsign names; tag those so both are findable.
    taken = {a["name"].strip().lower() for a in fs_apps}
    for app in moe_apps:
        base = app["name"]
        name = base
        n = 2
        while name.strip().lower() in taken:
            name = f"{base} (Moe{'' if n == 2 else ' ' + str(n)})"
            n += 1
        app["name"] = name

    seen = set()
    apps = []
    for app in fs_apps + moe_apps:
        key = (app["bundleIdentifier"].lower(), app.get("downloadURL", ""))
        if key in seen:
            continue
        seen.add(key)
        apps.append(app)

    apps.sort(key=lambda a: (a["name"].lower(), a["bundleIdentifier"].lower()))

    repo = {
        "name": REPO_NAME,
        "identifier": REPO_IDENTIFIER,
        "subtitle": REPO_SUBTITLE,
        "description": "Every app from fastsign.dev's repo plus Moe's App Hub in one Feather source.",
        "website": MOE,
        "iconURL": REPO_ICON,
        "META": {"repoName": REPO_NAME, "repoIcon": REPO_ICON},
        "userInfo": {},
        "apps": apps,
    }
    if SOURCE_URL:
        repo["sourceURL"] = SOURCE_URL

    # Minified + explicit newline="" so the file stays LF-only and as small as
    # possible; GitHub Pages gzips it further in transit.
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        json.dump(repo, f, ensure_ascii=False, separators=(",", ":"))

    print(f"wrote {OUT}: {len(apps)} apps total")
    print(f"  fastsign: {len(fs_apps)}  moe: {len(moe_apps)}")


if __name__ == "__main__":
    main()
