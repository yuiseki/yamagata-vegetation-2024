#!/usr/bin/env python3
"""Read the repository back from the Hub at the recorded revision and compare it with the local copy:
file checksums, row count, schema, CRS, bbox, geometry validity, value counts and NULL counts.

    uv run python scripts/08_verify_hub.py   # needs docs/revision.json from src/publish.py --push
"""

import hashlib
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq
import shapely
import veg
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).parents[1]


def main() -> int:
    rev = json.loads((ROOT / "docs" / "revision.json").read_text())
    repo, sha = rev["repo"], rev["revision"]
    out, bad = {"repo": repo, "revision": sha}, []
    cache = ROOT / "data" / "hub_readback"
    for name, want in rev["sha256"].items():
        p = Path(hf_hub_download(repo, name, repo_type="dataset", revision=sha, local_dir=cache))
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != want:
            bad.append(f"checksum {name}")
    out["files_checked"] = len(rev["sha256"])
    hub = cache / "parquet" / veg.PARQUET
    mine = ROOT / "data" / "parquet" / veg.PARQUET
    ph, pm = pq.ParquetFile(hub), pq.ParquetFile(mine)
    if ph.schema_arrow != pm.schema_arrow:
        bad.append("schema")
    gh = gpd.read_parquet(hub)
    gm = gpd.read_parquet(mine)
    prof = json.loads((ROOT / "docs" / f"{veg.PREF}_profile.json").read_text())
    out |= {"rows": len(gh), "crs": gh.crs.to_string(), "bbox": [float(x) for x in gh.total_bounds],
            "invalid": int((~shapely.is_valid(gh.geometry.values)).sum()), "schema": [f"{f.name}:{f.type}" for f in ph.schema_arrow]}  # fmt: skip
    if len(gh) != prof["polygons"]:
        bad.append("rows vs profile")
    if out["crs"] != prof["crs"] or out["bbox"] != prof["bbox"]:
        bad.append("crs or bbox")
    if out["invalid"]:
        bad.append("invalid geometry")
    cols = ["凡例コード", "作成年度", "植生区分", "source_file", "clipped"]
    out["value_counts"] = {
        c: {str(k): int(v) for k, v in gh[c].value_counts().sort_index().items()} for c in cols
    }
    for c in cols:
        if not gh[c].value_counts().sort_index().equals(gm[c].value_counts().sort_index()):
            bad.append(f"value counts {c}")
    out["nulls"] = {c: int(gh[c].isna().sum()) for c in gh.columns if c != "geometry"}
    if any(out["nulls"].values()):
        bad.append("nulls")
    if not pd.DataFrame(gh.drop(columns="geometry")).equals(
        pd.DataFrame(gm.drop(columns="geometry"))
    ):
        bad.append("attribute table differs from the local copy")
    if not (gh.geometry.to_wkb() == gm.geometry.to_wkb()).all():
        bad.append("geometry differs from the local copy")
    out["area_km2"] = float(gh["area_m2"].sum() / 1e6)
    out["problems"] = bad
    (ROOT / "docs" / "verify_hub.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n"
    )
    print(
        json.dumps(
            {k: v for k, v in out.items() if k not in ("schema", "value_counts")},
            ensure_ascii=False,
            indent=1,
        )
    )
    if bad:
        print("PROBLEMS:", bad, file=sys.stderr)
        return 1
    print("OK: the repository at", sha, "equals the local copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
