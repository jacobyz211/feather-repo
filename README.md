# Moe x FastSign — Feather repo

**Live source URL:** `https://jacobyz211.github.io/feather-repo/repo.json`

Add that URL in Feather → Sources → Add Source. Served by GitHub Pages as
`application/json` and gzipped in transit.

A single Feather/AltStore-format source that combines:

- **17,135 apps** from [fastsign.dev/repo.json](https://fastsign.dev/repo.json) (the full repo, not the 997-app lite one)
- **238 apps** from [moe.mohkg1017.pro](https://moe.mohkg1017.pro) (Moe's App Hub)

Fully merged: **17,368 apps**, deduplicated on bundle ID + download URL, sorted by name.
Moe entries show `Moe` as the developer; duplicates of fastsign names get a `(Moe)` suffix.

## Why it still loads fast

The upstream full repo is 23 MB. Feather downloads, decodes, and imports every app,
so the build rewrites each entry into the smallest shape Feather actually reads:

| Change | Effect |
| --- | --- |
| Drop the `versions` array | every upstream app has exactly one version, and it duplicates the top-level fields — **−5.9 MB** |
| Drop `icon`, `bundleID`, `fullDate` | exact duplicates of `iconURL`, `bundleIdentifier`, `versionDate` — **−2.2 MB** |
| Clip descriptions to 500 chars | median is 180, so only long outliers lose text — **−1.7 MB** |
| Minify JSON, LF-only | removes formatting whitespace |

Result: **14 MB raw, ~1.35 MB gzipped** — Feather still shows name, developer, icon,
version, date, size, minimum iOS, subtitle, tint color, and description for every app.
Feather resolves downloads from the top-level `downloadURL`, so nothing breaks;
the only loss is a version-history link for apps that never had more than one version.

## Files

| File | Purpose |
| --- | --- |
| `repo.json` | The source itself — this is the file you host. |
| `build_repo.py` | Rebuilds `repo.json` from both upstreams. |

## Using it in Feather

1. Open Feather → **Sources** (or Settings → Sources) → **Add Source**.
2. Paste `https://jacobyz211.github.io/feather-repo/repo.json`.

First import of ~17k apps will take a while — that's Feather inserting rows, not the
download. Once cached, the source list is instant.

To move it to your own host, upload `repo.json` to any static host that serves
`application/json`, then rebuild with `REPO_URL=https://your.domain/repo.json` so the
`sourceURL` field matches.

## Refreshing

Upstreams change often. Rerun:

```bash
REPO_URL=https://jacobyz211.github.io/feather-repo/repo.json python build_repo.py
git commit -am "Refresh apps" && git push
```

It re-downloads the fastsign JSON, scrapes all of Moe's catalog pages, and rewrites
`repo.json`. Requires only the Python standard library. GitHub Pages redeploys
automatically after the push.

## Notes on the data

- Moe's site does **not** publish a repo JSON, so its catalog is scraped from the
  listing pages (`data-*` attributes on each app card: version, size, bundle ID,
  icon, download URL, description, date).
- 32 Moe entries have no bundle ID upstream. They get a stable generated one
  (`pro.moe.<app-slug>.<id>`) so all of them stay visible and distinct in Feather.
- Google Drive share links from Moe are rewritten to direct
  `uc?export=download&id=…&confirm=t` URLs so Feather can fetch the IPA instead of
  an HTML page. Availability of those files is still controlled by Moe.
- Versions listed as `Latest` upstream stay as `Latest`.
- Many apps share a bundle ID (the full fastsign repo has thousands of variants).
  Feather keys entries on bundle ID + download URL, so all variants remain listed.

## Validation performed

- JSON parses; all 17,368 entries have name, bundle ID, version, date, HTTP icon,
  HTTP download URL, and integer size; descriptions are ≤ 500 chars.
- No duplicate bundle ID + download URL pairs, no relative icon URLs, no non-HTTP
  download links; all dates are `YYYY-MM-DD`.
- Checked Feather's `ASRepository.App` source: missing `versions` falls back to the
  top-level `version`, `versionDate`, and `downloadURL`.
- Could not run Feather itself (Windows host), so in-app import is untested.
