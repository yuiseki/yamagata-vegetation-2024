#!/usr/bin/env python3
"""List every legend of the raw source files (code, name, polygon count) and mark those whose
name contains one of the search words. Original spellings are kept; nothing is merged.

    uv run python scripts/03_legend_match.py   # writes docs/legend_all_source_raw.tsv, docs/legend_matches_source_raw.tsv
"""

import sys
from pathlib import Path

import pandas as pd
import pyogrio
import veg

ROOT = Path(__file__).parents[1]
WORDS = veg.WORDS


def main() -> int:
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    rows = []
    for name in veg.SOURCE_FILES:
        a = pyogrio.read_dataframe(run / name, read_geometry=False)
        g = (
            a.groupby(["凡例コード", "凡例名", "植生区分", "植生自然度"])
            .size()
            .reset_index(name="polygons")
        )
        g.insert(0, "file", name)
        rows.append(g)
    allv = pd.concat(rows, ignore_index=True)
    for w in WORDS:
        allv[f"has_{w}"] = allv["凡例名"].str.contains(w, regex=False)
    allv.to_csv(ROOT / "docs" / "legend_all_source_raw.tsv", sep="\t", index=False)
    hit = allv[allv[[f"has_{w}" for w in WORDS]].any(axis=1)]
    hit.to_csv(ROOT / "docs" / "legend_matches_source_raw.tsv", sep="\t", index=False)
    print(
        len(allv), "legend rows;", len(hit), "match;", hit["凡例コード"].nunique(), "distinct codes"
    )
    print(hit[["file", "凡例コード", "凡例名", "polygons"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
