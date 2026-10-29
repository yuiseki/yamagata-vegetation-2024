#!/usr/bin/env python3
"""Cut the source files at the prefecture boundary and write GeoParquet.

Rule (recorded in the card): a polygon that lies wholly inside the prefecture is kept as it is; a polygon that
crosses the boundary is clipped to it, so every stored polygon is inside the prefecture; a polygon that only
touches the boundary or whose overlap has no area is dropped. The cutter is the KSJ N03 (2026-01-01)
polygon of the prefecture, which is a boundary of administrative areas, not the coast line of the vegetation map.

    uv run python scripts/04_extract.py   # writes data/parquet/vegetation_<slug>.parquet and docs/extract_log.json
"""

import json
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely
import veg
from pyproj import Transformer

ROOT = Path(__file__).parents[1]


def boundary(run: Path):
    z = run.parents[1] / "docs" / veg.N03_ZIP
    shp = next(n for n in zipfile.ZipFile(z).namelist() if n.endswith(".shp"))
    g = gpd.read_file(f"zip://{z}!{shp}")
    assert set(g["N03_001"]) == {veg.JA} and g.crs.to_epsg() == 6668, (g.crs, set(g["N03_001"]))
    return g.geometry.union_all(), len(g)


def main() -> int:
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    cutter, n_polys = boundary(run)
    shapely.prepare(cutter)
    to_area = Transformer.from_crs(6668, veg.AREA_CRS, always_xy=True)

    def area_m2(g):
        return shapely.area(
            shapely.transform(g, lambda c: np.column_stack(to_area.transform(c[:, 0], c[:, 1])))
        )

    frames, log = (
        [],
        {"cutter": f"KSJ N03 20260101 {veg.CODE} ({veg.EN}), {n_polys} polygons dissolved", "area_crs": veg.AREA_CRS, "files": {}},
    )  # fmt: skip
    for name in veg.SOURCE_FILES:
        df = pyogrio.read_dataframe(run / name, bbox=tuple(cutter.bounds), fid_as_index=True)
        g = df.geometry.values
        inside, cross = veg.classify(g, cutter)
        hit = inside | cross
        if not hit.any():
            log["files"][name] = {"read_in_bbox": len(df), "intersect": 0, "wholly_inside": 0, "crossing": 0,
                                  "crossing_kept_after_clip": 0, "crossing_dropped_no_area": 0, "kept": 0}  # fmt: skip
            print(name, log["files"][name], flush=True)
            continue
        df["source_area_m2"] = area_m2(g)
        pieces = veg.clip_crossing(g[cross], cutter)
        keep_cross = np.array([x is not None for x in pieces], dtype=bool)
        whole = df[inside].assign(clipped=False)
        cut = df[cross][keep_cross].copy()
        cut["geometry"] = gpd.GeoSeries(
            [x for x in pieces if x is not None], index=cut.index, crs=df.crs
        )
        cut["clipped"] = True
        part = pd.concat([whole, cut])
        part["source_file"] = name
        log["files"][name] = {"read_in_bbox": len(df), "intersect": int(hit.sum()), "wholly_inside": int(inside.sum()),
                              "crossing": int(cross.sum()), "crossing_kept_after_clip": int(keep_cross.sum()),
                              "crossing_dropped_no_area": int((~keep_cross).sum()), "kept": len(part)}  # fmt: skip
        frames.append(part)
        print(name, log["files"][name], flush=True)
    if not frames:
        raise SystemExit("no polygon of the source files intersects the prefecture")
    res = gpd.GeoDataFrame(pd.concat(frames), geometry="geometry", crs=frames[0].crs)
    res.index.name = "fid"
    if res.index.has_duplicates:
        raise SystemExit("a fid occurs in both files")
    res["area_m2"] = area_m2(res.geometry.values)
    res = res.reset_index().sort_values("fid").reset_index(drop=True)
    res = res[veg.UNCUT_COLUMNS]
    log["rows"] = int(len(res))
    log["invalid_after"] = int((~shapely.is_valid(res.geometry.values)).sum())
    out = ROOT / "data" / "parquet"
    out.mkdir(parents=True, exist_ok=True)
    res.to_parquet(out / veg.PARQUET, compression="zstd", write_covering_bbox=True, index=False)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "extract_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=1) + "\n"
    )
    print(log["rows"], "rows; invalid", log["invalid_after"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
