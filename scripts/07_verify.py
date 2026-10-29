#!/usr/bin/env python3
"""Check the extract against the source files with a second engine (DuckDB spatial).

uv run python scripts/07_verify.py   # writes docs/verify_local.json, exits 1 on any difference
"""

import json
import sys
from pathlib import Path

import duckdb
import veg

ROOT = Path(__file__).parents[1]
ATTRS = veg.ATTRS


# Areas are compared in square degrees. Two area computations of the same polygon differ by floating-point and
# overlay noise that grows with the polygon (seen: 5e-12 square degrees, 1e-7 of a 4.6e-5 polygon on a very fine
# coast line, about 0.06 m2 of 460,000 m2, where the Python difference with the boundary is 5e-18). The
# tolerance is therefore 1e-12 plus 1e-6 of the polygon's own area (about 0.5 m2 for that polygon).
TOL = "1e-12 + 1e-6 * ST_Area(m.geometry)"


def main() -> int:
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    z = ROOT / "data" / "docs" / veg.N03_ZIP
    pq = ROOT / "data" / "parquet" / veg.PARQUET
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    con.execute("set preserve_insertion_order = false")
    shp = next(n for n in __import__("zipfile").ZipFile(z).namelist() if n.endswith(".shp"))
    src = " union all ".join(
        f"select '{n}' source_file, * from ST_Read('{run / n}')" for n in veg.SOURCE_FILES
    )
    con.execute(f"create table src as {src}")
    con.execute(f"create table mine as select * from read_parquet('{pq}')")
    res = {}
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    res["source_rows"] = q("select count(*) from src")
    res["rows"] = q("select count(*) from mine")
    res["fid_unique"] = q("select count(distinct fid) = count(*) from mine")
    # route 2: select the prefecture again. The N03 polygons of a prefecture do not overlap each other, so a
    # polygon has a positive overlap with the dissolved boundary iff it has one with at least one part, and the
    # area of its overlap with the boundary is the sum of its overlaps with the parts. Everything below is
    # therefore an indexed join against the undissolved parts; the dissolved polygon is not used (it needs
    # more memory than a 20 GB cap for the larger prefectures).
    con.execute(f"create table parts as select geom from ST_Read('/vsizip/{z}/{shp}')")
    con.execute(
        "create table cand as select s.fid, s.source_file, s.geom from src s "
        "semi join (select distinct s2.fid from src s2 join parts p on ST_Intersects(s2.geom, p.geom)) h using (fid)"
    )
    con.execute(
        "create table ov_cand as select c.fid, c.source_file, sum(ST_Area(ST_Intersection(c.geom, p.geom))) a "
        "from cand c join parts p on ST_Intersects(c.geom, p.geom) group by c.fid, c.source_file"
    )
    con.execute("create table sel as select fid, source_file from ov_cand where a > 0")
    con.execute(
        "create table ov_mine as select m.fid, sum(ST_Area(ST_Intersection(m.geometry, p.geom))) a "
        "from mine m join parts p on ST_Intersects(m.geometry, p.geom) group by m.fid"
    )
    res["reselected"] = q("select count(*) from sel")
    res["only_in_reselected"] = q(
        "select count(*) from sel where fid not in (select fid from mine)"
    )
    res["only_in_mine"] = q("select count(*) from mine where fid not in (select fid from sel)")
    res["source_file_differs"] = q(
        "select count(*) from mine m join sel s using (fid) where m.source_file <> s.source_file"
    )
    cond = " or ".join(f'm."{c}" is distinct from s."{c}"' for c in ATTRS)
    res["attribute_differences"] = q(
        f"select count(*) from mine m join src s using (fid) where {cond}"
    )
    res["unclipped_geometry_not_equal"] = q(
        "select count(*) from mine m join src s using (fid) where not m.clipped and not ST_Equals(m.geometry, s.geom)"
    )
    res["unclipped_wkb_not_identical"] = q(
        "select count(*) from mine m join src s using (fid) where not m.clipped and ST_AsWKB(m.geometry) <> ST_AsWKB(s.geom)"
    )
    res["clipped_outside_boundary"] = q(
        f"select count(*) from mine m left join ov_mine o using (fid) where m.clipped and ST_Area(m.geometry) - coalesce(o.a, 0) > {TOL}"
    )
    res["clipped_not_equal_to_intersection"] = q(
        f"select count(*) from mine m join ov_cand s using (fid) where m.clipped and abs(ST_Area(m.geometry) - s.a) > {TOL}"
    )
    res["clipped_without_source_overlap"] = q(
        "select count(*) from mine m where m.clipped and m.fid not in (select fid from ov_cand)"
    )
    res["clipped_larger_than_source"] = q(
        f"select count(*) from mine m join src s using (fid) where m.clipped and ST_Area(m.geometry) > ST_Area(s.geom) + {TOL}"
    )
    fid, ex, area = con.execute(
        "select m.fid, ST_Area(m.geometry) - coalesce(o.a, 0) e, ST_Area(m.geometry) from mine m "
        "left join ov_mine o using (fid) order by e desc limit 1"
    ).fetchone()
    res["max_outside_area_deg2"] = {"fid": fid, "excess": ex, "polygon_area": area, "ratio": ex / area}
    res["invalid"] = q("select count(*) from mine where not ST_IsValid(geometry)")
    res["clipped_rows"] = q("select count(*) from mine where clipped")
    res["unclipped_but_crossing"] = q(
        f"select count(*) from mine m left join ov_mine o using (fid) where not m.clipped and ST_Area(m.geometry) - coalesce(o.a, 0) > {TOL}"
    )
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "verify_local.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    bad = {
        k: v
        for k, v in res.items()
        if k
        in (
            "only_in_reselected",
            "only_in_mine",
            "source_file_differs",
            "attribute_differences",
            "unclipped_geometry_not_equal",
            "clipped_outside_boundary",
            "clipped_not_equal_to_intersection",
            "clipped_larger_than_source",
            "clipped_without_source_overlap",
            "invalid",
            "unclipped_but_crossing",
        )
        and v
    }
    if res["reselected"] != res["rows"] or not res["fid_unique"] or bad:
        print("DIFFERENCES:", bad, file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
