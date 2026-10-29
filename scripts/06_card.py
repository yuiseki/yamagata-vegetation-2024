#!/usr/bin/env python3
"""Write data/README.md (the dataset card), data/LICENSE and data/provenance.yaml from the measured docs.

uv run python scripts/06_card.py
"""

import json
from pathlib import Path

import pandas as pd
import veg

ROOT = Path(__file__).parents[1]
DATA = ROOT / "data"

ATTRIBUTION_JA = (
    f"出典：「現存植生図2024」（環境省生物多様性センター）（{veg.PAGE_URL}）、PDL1.0（{veg.PDL_URL}）。"
    "環境省生物多様性センターのデータを、yuiseki が{ja}境で切り出し、県境上のポリゴンを切り取り、"
    "GeoParquet に変換して作成した加工物であり、環境省が作成した未加工のデータではない。（取得日 {date}）"
)

CARD = """---
license: other
license_name: pdl-1.0
license_link: {pdl}
language:
- ja
tags:
- vegetation
- japan
- {slug}
- geospatial
- geoparquet
size_categories:
- {size_cat}
configs:
- config_name: default
  data_files: parquet/{parquet}
---

# 現存植生図2024 {ja} ({repo})

環境省生物多様性センターの「現存植生図2024」のうち、{ja}の部分を切り出して固定した GeoParquet です。
分析やモデルは含みません。原データの属性と意味を保持しています。

The {en} Prefecture part of 現存植生図2024 (Ministry of the Environment, Biodiversity Center of Japan; 1/25,000
vegetation survey, survey years {y0} to {y1} in {en}), frozen as GeoParquet. Original attributes are kept; nothing
is merged into classes of my own.

## Source and licence

- Source: 現存植生図2024, 環境省 自然環境局 生物多様性センター. Bulk downloads used: {files_list}, from the dataset
  record on G空間情報センター ({page}), the download that the Biodic page ({biodic}) and the 現存植生図2024
  information site ({story}) point to.{reused}
- The record has no version field; it was created {created} and its metadata modified {modified}. Per file (retrieval date;
  `Last-Modified` on the server; last_modified in the record):
{file_lines}
  sha256 of the source files are in `raw/{run}/MANIFEST.json`.
- Licence: 公共データ利用規約 第1.0版 (PDL1.0), as stated on the record (`public-data-license-v1.0`). PDL1.0 is
  compatible with CC BY 4.0. The conditions that apply: cite the source, and say that the data were edited and by
  whom, without presenting the result as an unprocessed State product. The Biodiversity Center names two cautions: do
  not infringe third-party rights, and legal limits such as the Survey Act where a GSI map is inside the content; none
  is stated for this data, and whether the base map of the survey carries such limits is not stated either.
- Attribution to use: {attribution}
- Cutter: the polygon of {en} in 国土数値情報 行政区域 (N03, 2026-01-01; MLIT), used only to cut and not republished.

## Files

| path | content |
| --- | --- |
| `parquet/{parquet}` | the data, {rows:,} MultiPolygons, GeoParquet, EPSG:6668 (JGD2011), zstd |
| `docs/legend_{slug}.tsv` | the {legends} legends present in {en}: code, name, 植生区分, 植生自然度, polygons, area |
| `docs/legend_matches_{slug}.tsv` | the legends whose name contains ブナ, ミズナラ, ナラ or コナラ |
| `docs/{slug}_profile.md`, `docs/{slug}_profile.json` | the verification and profile of this extract |
| `docs/raw_profile.md`, `docs/raw_profile.json` | the same for the source files before the cut |
| `docs/extract_log.json` | counts of the cut |
| `raw/{run}/MANIFEST.json`, `raw/{run}/ckan_record.json` | source files with sha256, HTTP headers and the record |

## Columns and their correspondence to the source

The source layer has 11 attributes, all text; they keep their names and values. The GeoPackage `fid` is the key of
the polygon over all Japan.

| column here | source | note |
| --- | --- | --- |
| `fid` | GeoPackage fid | unique over Japan; the key back to the source |
| `植生区分コード`, `大区分コード`, `中区分コード`, `細区分コード` | same names | text |
| `凡例コード` | same | text, 6 digits = 大区分 + 中区分 + 細区分 |
| `凡例名` | same | the community name by plant-sociological classification, original spelling ({src_legends} distinct legend codes in the source files) |
| `植生自然度`, `植生自然度区分`, `植生区分` | same | text |
| `作成年度` | same | text, year the polygon was made |
| `地域ブロック` | same | text, 1 北海道, 2 東北, 3 関東, 4 北陸, 5 中部, 6 近畿, 7 中四国, 8 九州沖縄; a block is a region and does not follow prefecture boundaries (values here: {blocks_txt}) |
| `source_file` | added | the file the polygon comes from (here: {files_txt}) |
| `clipped` | added | true when the polygon crossed the {en} boundary and was cut to it |
| `source_area_m2` | added | area of the polygon before the cut, in EPSG:6678 |
| `area_m2` | added | area of the stored polygon, in EPSG:6678 (JGD2011 / Plane Rectangular CS X) |
| `geometry` | geom | MultiPolygon (the GeoPackage layer is declared Polygon but stores MultiPolygons) |

## How {en} was cut

1. Polygons of the source files that intersect the N03 polygon of {en} were selected ({per_file}).
2. {inside:,} polygons lie wholly inside and are kept as they are.
3. {clipped:,} polygons cross the boundary and are clipped to it (their area before the cut was {src_clip:.1f} km2, after the
   cut {after_clip:.1f} km2); `clipped` marks them and `source_area_m2` keeps the original area. {dropped_txt}
4. The N03 boundary is an administrative boundary and not the coast line of the vegetation map. The stored polygons add
   up to {area:.3f} km2 against {n03_area:.3f} km2 for the N03 polygon ({share:.5f}% of its area, difference {diff:+.3f} km2){diff_txt}

## What is in it

- {rows:,} polygons, {area:.1f} km2, {nulls_txt}, {invalid} invalid and {empty} empty geometries.
- area by 地域ブロック: {blocks_area}.{block_note}
- 作成年度 (polygons): {years}
- {legends} legends are present. {m_codes} of them contain ブナ, ミズナラ, ナラ or コナラ in the name ({m_polys:,} polygons;
  the legends overlap in meaning, so the areas are not to be added as one class):

{match_table}

The match is by substring on the original name. {match_notes}
A polygon is one community; the legend does not give the share of a species.

## Cautions

- Polygons were surveyed in different years (see 作成年度); the extract is not a snapshot of one year.
- {pairs} pairs of polygons overlap by slivers (the largest about {max_overlap_m2:.0f} m2); they are kept as in the source, not repaired.
- The polygons that were cut at the boundary have edges that come from the N03 boundary, not from the survey.
- All numeric-looking attributes are text, as in the source.
- The source data may change on the publisher's side; this is the copy retrieved on {date}.

## Verification

`scripts/07_verify.py` reads the source files again, selects {en} with a second engine (DuckDB spatial), and checks
that the same fids are kept, that the 11 attributes are equal for every polygon, that unclipped geometries are
byte-equal to the source, and that clipped ones are inside the boundary and no larger than the source (areas are
compared with a tolerance of 1e-12 plus 1e-6 of the polygon's own area, because two computations of the area of a
very fine coast-line polygon differ by that much; the largest excess found is `max_outside_area_deg2` in
`docs/verify_local.json`). After the
upload, `scripts/08_verify_hub.py` reads this repository back at a fixed revision and compares it with the local copy.
The revision is recorded in `docs/revision.md` of the GitHub repository ({github}).

Reproduce: `uv run python scripts/01_download.py`, then `02` to `08` in order.
"""


def main() -> None:
    run = sorted((DATA / "raw").glob("*/MANIFEST.json"))[-1].parent
    man = json.loads((run / "MANIFEST.json").read_text())
    rec = json.loads((run / "ckan_record.json").read_text())
    prof = json.loads((ROOT / "docs" / f"{veg.PREF}_profile.json").read_text())
    log = json.loads((ROOT / "docs" / "extract_log.json").read_text())
    hit = pd.read_csv(
        ROOT / "docs" / f"legend_matches_{veg.PREF}.tsv", sep="\t", dtype={"凡例コード": str}
    )
    srcleg = pd.read_csv(ROOT / "docs" / "legend_all_source_raw.tsv", sep="\t", dtype={"凡例コード": str})
    date = " / ".join(sorted({v["retrieved"] for n, v in man["files"].items() if n.endswith(".gpkg")}))
    rows = ["| 凡例コード | 凡例名 | polygons | area km2 |", "| --- | --- | ---: | ---: |"]
    rows += [
        f"| {r.凡例コード} | {r.凡例名} | {r.polygons:,} | {r.area_km2:.2f} |"
        for r in hit.itertuples()
    ]
    f = log["files"]
    years = ", ".join(f"{k}: {v:,}" for k, v in prof["value_counts"]["作成年度"].items())
    attribution = ATTRIBUTION_JA.format(date=date, ja=veg.JA)
    holding = [n for n in veg.SOURCE_FILES if f[n]["kept"]]
    files_list = ", ".join(f"`{n}` ({veg.BLOCK_NAMES.get(n[9], '')})" for n in veg.SOURCE_FILES)
    per_file = f"{len(holding)} of the {len(veg.SOURCE_FILES)} source files hold parts of {veg.EN}: " + ", ".join(
        f"{f[n]['kept']:,} polygons from `{n[7:].split('.')[0]}`" for n in holding
    )
    dropped = sum(x["crossing_dropped_no_area"] for x in f.values())
    nulls = sum(prof["nulls"].values())
    reused = ""
    if man.get("reused"):
        reused = (
            " Some files were first retrieved for another repository of this series; they were hard-linked here after their sha256 was checked against"
            " the MANIFEST and the size and last_modified of the record were found unchanged."
        )
    names = [n for n in man["files"] if n.endswith(".gpkg")]
    blocks = prof["value_counts"]["地域ブロック"]
    file_lines = "\n".join(
        f"  - `{n}`: retrieved {man['files'][n]['retrieved']}; {man['files'][n]['http']['last-modified']}; {man['files'][n]['record_last_modified'][:10]}"
        for n in names
    )
    other = [k for k in blocks if k != "2"]
    block_note = ""
    if other:
        block_note = (
            " Parts of {en} lie outside the Tohoku block: cutting the Tohoku files alone would have covered {tohoku_share:.2f}% of the N03 area."
            " The file of each of the other blocks was cut in the same way ({others})."
        ).format(
            en=veg.EN, tohoku_share=prof["area_km2_by_block"].get("2", 0) / prof["n03_area_km2"] * 100,
            others=", ".join(f"{veg.BLOCK_NAMES[k]} (地域ブロック {k})" for k in other),
        )
    card = CARD.format(
        pdl=veg.PDL_URL, page=veg.PAGE_URL, biodic=veg.BIODIC_PAGE_URL, story=veg.STORY_URL, date=date, run=run.name,
        created=rec["metadata_created"][:10], modified=rec["metadata_modified"][:10],
        attribution=attribution, rows=prof["polygons"], legends=prof["legends"],
        slug=veg.PREF, ja=veg.JA, en=veg.EN, repo=veg.REPO, parquet=veg.PARQUET, size_cat=veg.size_category(prof["polygons"]),
        y0=prof["survey_year_min"], y1=prof["survey_year_max"], reused=reused, file_lines=file_lines, files_list=files_list,
        blocks_txt=", ".join(f"{k}: {v:,} polygons" for k, v in blocks.items()),
        blocks_area=", ".join(f"{k} {veg.BLOCK_NAMES[k]} {v:.1f} km2" for k, v in prof["area_km2_by_block"].items()), block_note=block_note,
        src_legends=srcleg["凡例コード"].nunique(), per_file=per_file,
        inside=sum(x["wholly_inside"] for x in f.values()),
        clipped=prof["clipped"], src_clip=prof["source_area_km2_of_clipped_polygons"],
        after_clip=prof["area_km2_clipped_part"], share=prof["share_of_n03_area"] * 100, area=prof["area_km2_total"],
        n03_area=prof["n03_area_km2"], files_txt=", ".join(f"`{n}`" for n in holding),
        diff_txt="." if abs(prof["area_km2_total"] - prof["n03_area_km2"]) < 0.01 else "; the difference is not explained here.", diff=prof["area_km2_total"] - prof["n03_area_km2"],
        dropped_txt="None disappeared in the cut." if dropped == 0 else f"{dropped:,} crossing polygons had no area inside and were dropped.",
        nulls_txt="no NULL in any column" if nulls == 0 else f"{nulls:,} NULLs in all columns",
        invalid=prof["invalid"], empty=prof["empty"], years=years, m_codes=prof["legend_matches"]["codes"],
        m_polys=prof["legend_matches"]["polygons"], match_table="\n".join(rows), match_notes=" ".join(prof["match_notes"]),
        pairs=prof["overlapping_pairs_with_area"], max_overlap_m2=prof["max_overlap_m2"],
        github=f"https://github.com/yuiseki/{veg.REPO}",
    )  # fmt: skip
    (DATA / "README.md").write_text(card, encoding="utf-8")
    (DATA / "LICENSE").write_text(
        "公共データ利用規約（第1.0版）PDL1.0 (" + veg.PDL_URL + ")\n\n"
        "The data are 現存植生図2024 of the Biodiversity Center of Japan (Ministry of the Environment), published under PDL1.0,\n"
        "which is compatible with CC BY 4.0. They were processed as described in README.md.\n\n"
        + attribution
        + "\n",
        encoding="utf-8",
    )
    (DATA / "provenance.yaml").write_text(
        f"source: 現存植生図2024 (環境省生物多様性センター)\nurl: {veg.PAGE_URL}\nlicense: PDL1.0\n"
        f"retrieved: {date}\nrecord_metadata_modified: {rec['metadata_modified']}\n"
        f"files:\n"
        + "".join(
            f"  - {n}: {v['sha256']}\n" for n, v in man["files"].items() if n.endswith(".gpkg")
        )
        + f"cutter: {veg.N03_URL}\nrows: {prof['polygons']}\n",
        encoding="utf-8",
    )
    print("wrote card, LICENSE, provenance.yaml")


if __name__ == "__main__":
    main()
