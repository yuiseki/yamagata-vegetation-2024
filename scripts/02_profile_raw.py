#!/usr/bin/env python3
"""Profile the raw source files as they are (no cutting): layers, rows, geometry type, CRS, bbox,
invalid geometries, columns, legend values, survey years, nulls. The files are those of veg.SOURCE_FILES.

    uv run python scripts/02_profile_raw.py   # writes docs/raw_profile.json and docs/raw_profile.md
"""

import json
import sys
from pathlib import Path

import numpy as np
import pyogrio
import shapely
import veg

ROOT = Path(__file__).parents[1]


def profile(path: Path) -> dict:
    layers = pyogrio.list_layers(path)
    out = {"file": path.name, "layers": [[str(a), str(b)] for a, b in layers]}
    layer = str(layers[0][0])
    info = pyogrio.read_info(path, layer=layer)
    out |= {"rows": int(info["features"]), "crs": str(info["crs"]), "geometry_type": info["geometry_type"],
            "fields": [str(f) for f in info["fields"]], "dtypes": [str(d) for d in info["dtypes"]]}  # fmt: skip
    attrs = pyogrio.read_dataframe(path, layer=layer, read_geometry=False)
    out["nulls"] = {c: int(attrs[c].isna().sum()) for c in attrs.columns}
    out["empty_strings"] = {
        c: int((attrs[c] == "").sum()) for c in attrs.columns if attrs[c].dtype == object
    }
    for col in ("作成年度", "植生区分コード", "植生区分", "地域ブロック", "植生自然度"):
        out[f"value_counts:{col}"] = {
            str(k): int(v) for k, v in attrs[col].value_counts(dropna=False).sort_index().items()
        }
    leg = attrs.groupby(["凡例コード", "凡例名"], dropna=False).size().reset_index(name="n")
    out["legend_n"] = int(len(leg))
    out["legend_codes_with_several_names"] = sorted(
        leg.groupby("凡例コード")
        .filter(lambda g: len(g) > 1)["凡例コード"]
        .astype(str)
        .unique()
        .tolist()
    )
    out["fid_unique"] = bool(attrs["fid"].is_unique) if "fid" in attrs.columns else None
    geo = pyogrio.read_dataframe(path, layer=layer, columns=[])
    g = geo.geometry.values
    out["bbox"] = [float(x) for x in geo.total_bounds]
    out["geometry_types"] = {
        str(k): int(v)
        for k, v in zip(*np.unique(shapely.get_type_id(g), return_counts=True), strict=True)
    }
    out["null_geometry"] = int(shapely.is_missing(g).sum())
    out["empty_geometry"] = int(shapely.is_empty(g).sum())
    out["invalid_geometry"] = int((~shapely.is_valid(g)).sum())
    return out


def raw_markdown(run: Path, res: dict) -> str:
    names = list(res)
    man = json.loads((run / "MANIFEST.json").read_text())
    when = ", ".join(sorted({man["files"][n]["retrieved"] for n in names}))

    def row(label, f):
        return f"| {label} | " + " | ".join(f(res[n]) for n in names) + " |"

    def years(p):
        return ", ".join(f"{k}:{v}" for k, v in p["value_counts:作成年度"].items())

    md = [
        "# Raw profile of the source files of 現存植生図2024 (before any cutting)",
        "",
        f"Source: G空間情報センター record `biodic_veg2024`, files retrieved {when} (sha256 in data/raw/{run.name}/MANIFEST.json, kept in the Hugging Face repo).",
        "",
        "| item | " + " | ".join(names) + " |",
        "| --- | " + " | ".join("---" for _ in names) + " |",
        row("layers", lambda p: ", ".join(f"{a} ({b})" for a, b in p["layers"])),
        row("rows", lambda p: f"{p['rows']:,}"),
        row("geometry stored (shapely type id; 3 Polygon, 6 MultiPolygon)", lambda p: str(p["geometry_types"])),
        row("CRS", lambda p: p["crs"]),
        row("bbox lon/lat", lambda p: ", ".join(f"{x:.4f}" for x in p["bbox"])),
        row("invalid geometries", lambda p: str(p["invalid_geometry"])),
        row("null / empty geometries", lambda p: f"{p['null_geometry']} / {p['empty_geometry']}"),
        row("distinct legends (凡例コード x 凡例名)", lambda p: str(p["legend_n"])),
        row("codes with more than one name", lambda p: str(len(p["legend_codes_with_several_names"]))),
        row("NULLs in any attribute", lambda p: str(sum(p["nulls"].values()))),
        row("地域ブロック values", lambda p: str(p["value_counts:地域ブロック"])),
        row("作成年度 values", years),
        "",
        f"Columns (all stored as text, {len(res[names[0]]['fields'])} attributes plus the GeoPackage fid): " + ", ".join(res[names[0]]["fields"]) + ".",
        "",
        "Notes",
        "- The layer is declared Polygon in the GeoPackage; the line `geometry stored` above gives what is really stored.",
        "- 地域ブロック: 1 北海道, 2 東北, 3 関東, 4 北陸, 5 中部, 6 近畿, 7 中四国, 8 九州沖縄. A block is a region and does not follow prefecture boundaries; which file holds which part of the prefecture is recorded when it is cut out (`extract_log.json`).",
        "- The numeric-looking columns (作成年度, 植生自然度) are text in the source and kept as such.",
        "- `legend_all_source_raw.tsv` lists every legend; `legend_matches_source_raw.tsv` lists the legends whose name contains ブナ, ミズナラ, ナラ or コナラ, in the original spelling. The match is by substring, so it also catches other species whose names contain these words; nothing was merged.",
    ]
    return "\n".join(md) + "\n"


def main() -> int:
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    res = {name: profile(run / name) for name in veg.SOURCE_FILES}
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "raw_profile.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1) + "\n"
    )
    (ROOT / "docs" / "raw_profile.md").write_text(raw_markdown(run, res), encoding="utf-8")
    for name, p in res.items():
        print(
            name,
            p["rows"],
            p["crs"][:40],
            p["geometry_types"],
            "invalid",
            p["invalid_geometry"],
            "legends",
            p["legend_n"],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
