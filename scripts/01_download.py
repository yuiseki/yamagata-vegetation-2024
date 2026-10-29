#!/usr/bin/env python3
"""Fetch the source files of 現存植生図2024 for this prefecture (veg.SOURCE_FILES) and its boundary (the cutter)
with checksums.

    uv run python scripts/01_download.py                          # download everything
    uv run python scripts/01_download.py --from-run DIR [--from-run DIR2]   # reuse GeoPackages of earlier runs

The record on G空間情報センター is read first and the run stops if its licence is no longer
public-data-license-v1.0. The files are fetched with aria2c (resumable) from the signed S3 link that the
record's download URL redirects to.

--from-run DIR points at a run directory (with MANIFEST.json) that already holds some of the files, for
example that of another prefecture repository. Those files are hard-linked (or copied) instead of fetched
again, after their sha256 is checked against that MANIFEST and the size and last_modified of the resource
are checked against the record as it is now. A difference stops the run: the publisher has corrected the
data. Files that no run holds are fetched. The run directory is named after the latest retrieval date.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

import veg

ROOT = Path(__file__).parents[1]


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": veg.UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def probe(url: str) -> tuple[str, dict]:
    """Resolve the redirect to the signed link and read the headers of a one-byte range."""
    out = subprocess.run(
        ["curl", "-sS", "-L", "-A", veg.UA, "-r", "0-0", "-D", "-", "-o", "/dev/null",
         "-w", "\n@@%{url_effective}", url],
        check=True, capture_output=True, text=True,
    ).stdout.replace("\r", "")  # fmt: skip
    final = out.rsplit("@@", 1)[1].strip()
    last = [h for h in out.split("\n\n") if h.startswith("HTTP/")][-1]
    pick = {}
    for line in last.splitlines()[1:]:
        k, _, v = line.partition(":")
        if k.lower() in ("etag", "last-modified", "content-range"):
            pick[k.lower()] = v.strip()
    return final, pick


def curl(url: str, dest: Path, connections: int = 8) -> dict:
    """Fetch url into dest. The host serves about 100 KB/s per connection, so a few ranged
    connections are used (aria2c, resumable); the signed link lives one hour, so it is
    resolved again whenever a round ends before the file is whole."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    head = {}
    for _ in range(20):
        final, head = probe(url)
        total = int(head["content-range"].rsplit("/", 1)[1]) if "content-range" in head else None
        if (
            dest.exists()
            and total
            and dest.stat().st_size == total
            and not dest.with_name(dest.name + ".aria2").exists()
        ):
            return head
        subprocess.run(["aria2c", "-c", "-x", str(connections), "-s", str(connections), "-k", "4M",
                        "--user-agent", veg.UA, "--summary-interval=60", "--console-log-level=warn",
                        "-d", str(dest.parent), "-o", dest.name, final], check=False)  # fmt: skip
    raise SystemExit(f"could not fetch {url}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 24):
            h.update(chunk)
    return h.hexdigest()


def link_or_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


def iso(run: str) -> str:
    return f"{run[:4]}-{run[4:6]}-{run[6:]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-run", type=Path, action="append", default=[], help="run directory to reuse files from")
    a = ap.parse_args()
    prevs = [(d, json.loads((d / "MANIFEST.json").read_text())) for d in a.from_run]
    held = {}  # file name -> (run dir, manifest entry, date retrieved)
    for d, m in prevs:
        for name, f in m["files"].items():
            if name in veg.SOURCE_FILES:
                held[name] = (d, f, f.get("retrieved") or iso(m["run"]))
    today = date.today().strftime("%Y%m%d")
    stamps = [h[2].replace("-", "") for h in held.values()]
    if len(held) < len(veg.SOURCE_FILES):
        stamps.append(today)
    run = max(stamps)
    out = ROOT / "data" / "raw" / run
    out.mkdir(parents=True, exist_ok=True)
    record = json.loads(get(veg.CKAN_URL))["result"]
    if record["license_id"] != veg.LICENSE_ID:
        raise SystemExit(f"the licence of the record changed: {record['license_id']}")
    keep = ("id", "name", "title", "license_id", "license_title", "license_url", "metadata_created",
            "metadata_modified", "author", "maintainer", "notes")  # fmt: skip
    meta = {k: record.get(k) for k in keep}
    meta["organization"] = record["organization"]["title"]
    meta["resources"] = [{k: r.get(k) for k in ("name", "format", "url", "size", "last_modified")}
                         for r in record["resources"]]  # fmt: skip
    (out / "ckan_record.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
    by_name = {r["url"].rsplit("/", 1)[1]: r for r in record["resources"] if r["format"] == "gpkg"}
    manifest = {"run": run, "record": veg.PAGE_URL, "record_metadata_modified": meta["metadata_modified"], "files": {}}
    reused = []
    for name in veg.SOURCE_FILES:
        r = by_name[name]
        if name in held:
            d, f, when = held[name]
            if int(r["size"]) != f["size"] or r["last_modified"] != f["record_last_modified"]:
                raise SystemExit(f"{name}: the record changed (size {r['size']}, {r['last_modified']})")
            link_or_copy(d / name, out / name)
            if sha256(out / name) != f["sha256"]:
                raise SystemExit(f"{name}: sha256 differs from the MANIFEST of {d}")
            manifest["files"][name] = {**f, "retrieved": when}
            reused.append(f"{name} from {d.parents[2].name if d.parent.name == 'raw' else d.name} ({when})")
            print(name, f["size"], "reused, sha256 ok")
            continue
        head = curl(r["url"], out / name)
        size = (out / name).stat().st_size
        if size != int(r["size"]):
            raise SystemExit(f"{name}: {size} bytes, the record says {r['size']}")
        manifest["files"][name] = {"url": r["url"], "size": size, "sha256": sha256(out / name),
                                   "record_last_modified": r["last_modified"], "http": head,
                                   "retrieved": iso(today)}  # fmt: skip
        print(name, size)
    if reused:
        manifest["reused"] = reused
    docs = ROOT / "data" / "docs"
    head = curl(veg.N03_URL, docs / veg.N03_ZIP)
    manifest["files"][veg.N03_ZIP] = {
        "url": veg.N03_URL, "size": (docs / veg.N03_ZIP).stat().st_size,
        "sha256": sha256(docs / veg.N03_ZIP), "http": head, "role": "cutter only"}  # fmt: skip
    (out / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("wrote", out / "MANIFEST.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
