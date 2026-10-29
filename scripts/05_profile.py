#!/usr/bin/env python3
"""Verify and profile the extract: polygons, area, legends, survey years, NULLs, validity.

uv run python scripts/05_profile.py   # writes docs/<slug>_profile.json, legend_<slug>.tsv, legend_matches_<slug>.tsv, <slug>_profile.md
"""

import json
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import veg
from pyproj import Transformer

ROOT = Path(__file__).parents[1]
DOCS = ROOT / "docs"


def main() -> int:
    df = gpd.read_parquet(ROOT / "data" / "parquet" / veg.PARQUET)
    g = df.geometry.values
    res = {
        "polygons": len(df),
        "crs": df.crs.to_string(),
        "bbox": [float(x) for x in df.total_bounds],
    }
    res["geometry_types"] = df.geometry.geom_type.value_counts().to_dict()
    res["invalid"] = int((~shapely.is_valid(g)).sum())
    res["empty"] = int(shapely.is_empty(g).sum())
    res["fid_unique"] = bool(df["fid"].is_unique)
    res["nulls"] = {c: int(df[c].isna().sum()) for c in df.columns if c != "geometry"}
    res["clipped"] = int(df["clipped"].sum())
    res["by_source_file"] = df["source_file"].value_counts().to_dict()
    res["area_crs"] = veg.AREA_CRS
    res["area_km2_total"] = float(df["area_m2"].sum() / 1e6)
    res["area_km2_by_block"] = {
        k: float(v / 1e6) for k, v in df.groupby("地域ブロック")["area_m2"].sum().sort_index().items()
    }
    res["area_km2_clipped_part"] = float(df.loc[df["clipped"], "area_m2"].sum() / 1e6)
    res["source_area_km2_of_clipped_polygons"] = float(
        df.loc[df["clipped"], "source_area_m2"].sum() / 1e6
    )
    z = ROOT / "data" / "docs" / veg.N03_ZIP
    shp = next(n for n in zipfile.ZipFile(z).namelist() if n.endswith(".shp"))
    pref = gpd.read_file(f"zip://{z}!{shp}").to_crs(veg.AREA_CRS).geometry.union_all()
    res["n03_area_km2"] = float(pref.area / 1e6)
    res["share_of_n03_area"] = res["area_km2_total"] / res["n03_area_km2"]
    # overlap among polygons: the area of the intersection of every pair that intersects
    tree = shapely.STRtree(g)
    a, b = tree.query(g, predicate="intersects")
    pair = a < b
    inter = shapely.area(shapely.intersection(g[a[pair]], g[b[pair]]))
    res["overlapping_pairs_with_area"] = int((inter > 1e-12).sum())  # square degrees
    res["max_overlap_deg2"] = float(inter.max()) if len(inter) else 0.0
    res["max_overlap_m2"] = 0.0
    if len(inter) and inter.max() > 0:
        i = int(np.argmax(inter))
        big = shapely.intersection(g[a[pair]][i], g[b[pair]][i])
        to_area = Transformer.from_crs(6668, veg.AREA_CRS, always_xy=True)
        big = shapely.transform(big, lambda c: np.column_stack(to_area.transform(c[:, 0], c[:, 1])))
        res["max_overlap_m2"] = float(shapely.area(big))
    res["value_counts"] = {
        c: df[c].value_counts().sort_index().to_dict()
        for c in ["作成年度", "植生区分", "植生自然度", "植生自然度区分", "地域ブロック"]
    }
    res["survey_year_min"] = int(min(res["value_counts"]["作成年度"], key=int))
    res["survey_year_max"] = int(max(res["value_counts"]["作成年度"], key=int))
    leg = (
        df.groupby(["凡例コード", "凡例名", "植生区分", "植生自然度"])
        .agg(polygons=("fid", "size"), area_km2=("area_m2", lambda s: s.sum() / 1e6))
        .reset_index()
    )
    leg.to_csv(DOCS / f"legend_{veg.PREF}.tsv", sep="\t", index=False)
    mask = pd.concat([leg["凡例名"].str.contains(w, regex=False) for w in veg.WORDS], axis=1).any(axis=1)
    hit = leg[mask].copy()
    for w in veg.WORDS:
        hit[f"has_{w}"] = hit["凡例名"].str.contains(w, regex=False)
    hit.to_csv(DOCS / f"legend_matches_{veg.PREF}.tsv", sep="\t", index=False)
    res["legends"] = int(len(leg))
    res["legend_matches"] = {
        "codes": int(len(hit)),
        "polygons": int(hit["polygons"].sum()),
        "area_km2": float(hit["area_km2"].sum()),
        "codes_with_word": {w: int(hit[f"has_{w}"].sum()) for w in veg.WORDS},
        "polygons_with_word": {w: int(hit.loc[hit[f"has_{w}"], "polygons"].sum()) for w in veg.WORDS},
    }
    res["match_notes"] = veg.match_notes(hit.to_dict("records"))
    res["year_by_legend_match"] = (
        df[df["凡例コード"].isin(hit["凡例コード"])]["作成年度"].value_counts().sort_index().to_dict()
    )
    log = json.loads((DOCS / "extract_log.json").read_text())
    inside = sum(f["wholly_inside"] for f in log["files"].values())
    dropped = sum(f["crossing_dropped_no_area"] for f in log["files"].values())
    drop_txt = "none dropped" if dropped == 0 else f"{dropped:,} crossing polygons had no area inside and were dropped"
    diff = res["area_km2_total"] - res["n03_area_km2"]
    md = [
        f"# {veg.EN} extract of 現存植生図2024: verification and profile",
        "",
        f"- polygons: {res['polygons']:,} ({', '.join(f'{v:,} {k}' for k, v in res['geometry_types'].items())}), CRS {res['crs']}, bbox lon {res['bbox'][0]:.4f} to {res['bbox'][2]:.4f}, lat {res['bbox'][1]:.4f} to {res['bbox'][3]:.4f}",
        f"- source files: {res['by_source_file']}",
        f"- cut: {inside:,} polygons wholly inside {veg.EN} kept as they are; {res['clipped']:,} polygons that cross the boundary were clipped to it ({drop_txt}); the clipped polygons had {res['source_area_km2_of_clipped_polygons']:.1f} km2 before the cut and keep {res['area_km2_clipped_part']:.1f} km2",
        f"- area: {res['area_km2_total']:.3f} km2 in EPSG:{veg.AREA_CRS}, against {res['n03_area_km2']:.3f} km2 for the N03 polygon of {veg.EN} ({res['share_of_n03_area'] * 100:.5f}%, difference {diff:+.3f} km2)",
        "- area by 地域ブロック: " + ", ".join(f"{k} {veg.BLOCK_NAMES.get(k, '')} {v:.3f} km2 ({v / res['n03_area_km2'] * 100:.2f}% of N03)" for k, v in res["area_km2_by_block"].items()),
        f"- geometry validity: {res['invalid']} invalid, {res['empty']} empty; fid unique: {res['fid_unique']}",
        f"- overlaps: {res['overlapping_pairs_with_area']} pairs of polygons overlap by a sliver (largest {res['max_overlap_deg2']:.2e} square degrees, about {res['max_overlap_m2']:.0f} m2); not repaired",
        f"- NULLs: {sum(res['nulls'].values())} in all columns",
        "",
        "## 作成年度 (polygons)",
        "",
        "| year | polygons |",
        "| --- | ---: |",
    ]
    md += [f"| {k} | {v:,} |" for k, v in res["value_counts"]["作成年度"].items()]
    md += [
        "",
        "## Legends whose name contains ブナ, ミズナラ, ナラ or コナラ",
        "",
        f"{res['legend_matches']['codes']} of the {res['legends']} legends present in {veg.EN}; {res['legend_matches']['polygons']:,} polygons, {res['legend_matches']['area_km2']:.1f} km2 together (the legends overlap in meaning, do not read this as one class).",
        "",
        "| code | name (original) | polygons | area km2 | ブナ | ミズナラ | ナラ | コナラ |",
        "| --- | --- | ---: | ---: | :-: | :-: | :-: | :-: |",
    ]
    for r in hit.itertuples(index=False):
        md.append(
            f"| {r[0]} | {r[1]} | {r[4]:,} | {r[5]:.2f} | "
            + " | ".join("x" if getattr(r, f"has_{w}") else "" for w in veg.WORDS)
            + " |"
        )
    md += ["", "The match is by substring on the original name. " + " ".join(res["match_notes"]),
           f"The full list of {veg.EN} legends is `legend_{veg.PREF}.tsv`.", "",
           "## 作成年度 of the polygons of those legends", "", "| year | polygons |", "| --- | ---: |"]  # fmt: skip
    md += [f"| {k} | {v:,} |" for k, v in res["year_by_legend_match"].items()]
    (DOCS / f"{veg.PREF}_profile.md").write_text("\n".join(md) + "\n")
    (DOCS / f"{veg.PREF}_profile.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("value_counts", "nulls", "year_by_legend_match")},
                     ensure_ascii=False, indent=1))  # fmt: skip
    print(hit[["凡例コード", "凡例名", "polygons", "area_km2"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
