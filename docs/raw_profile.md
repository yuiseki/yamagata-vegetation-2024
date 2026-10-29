# Raw profile of the source files of 現存植生図2024 (before any cutting)

Source: G空間情報センター record `biodic_veg2024`, files retrieved 2026-10-28, 2026-10-29 (sha256 in data/raw/20261029/MANIFEST.json, kept in the Hugging Face repo).

| item | veg2024bk2a.gpkg | veg2024bk2b.gpkg | veg2024bk4.gpkg |
| --- | --- | --- | --- |
| layers | veg2024bk2a (Polygon) | veg2024bk2b (Polygon) | veg2024bk4 (Polygon) |
| rows | 591,487 | 587,145 | 306,443 |
| geometry stored (shapely type id; 3 Polygon, 6 MultiPolygon) | {'6': 591487} | {'6': 587145} | {'6': 306443} |
| CRS | EPSG:6668 | EPSG:6668 | EPSG:6668 |
| bbox lon/lat | 139.2468, 36.8364, 141.6215, 39.3362 | 139.6216, 38.6696, 142.1214, 41.5859 | 135.4971, 35.3365, 139.9964, 38.6696 |
| invalid geometries | 0 | 0 | 0 |
| null / empty geometries | 0 / 0 | 0 / 0 | 0 / 0 |
| distinct legends (凡例コード x 凡例名) | 221 | 189 | 210 |
| codes with more than one name | 0 | 0 | 0 |
| NULLs in any attribute | 0 | 0 | 0 |
| 地域ブロック values | {'2': 591487} | {'2': 587145} | {'4': 306443} |
| 作成年度 values | 2000:79732, 2001:13829, 2002:38884, 2003:43126, 2006:55546, 2009:11743, 2013:15979, 2015:86248, 2016:7257, 2017:76175, 2018:47676, 2020:115292 | 2000:26822, 2001:21917, 2003:31232, 2005:13150, 2007:8411, 2008:41938, 2010:26104, 2012:15567, 2013:34266, 2014:78016, 2015:97247, 2016:9291, 2017:9064, 2018:20444, 2020:69099, 2022:84577 | 2000:12529, 2001:58743, 2003:16524, 2004:23371, 2005:15290, 2006:28510, 2007:9197, 2009:15354, 2011:23218, 2012:16818, 2013:21186, 2015:9775, 2016:29431, 2017:19351, 2018:7146 |

Columns (all stored as text, 11 attributes plus the GeoPackage fid): 植生区分コード, 大区分コード, 中区分コード, 細区分コード, 凡例コード, 凡例名, 植生自然度, 植生自然度区分, 植生区分, 作成年度, 地域ブロック.

Notes
- The layer is declared Polygon in the GeoPackage; the line `geometry stored` above gives what is really stored.
- 地域ブロック: 1 北海道, 2 東北, 3 関東, 4 北陸, 5 中部, 6 近畿, 7 中四国, 8 九州沖縄. A block is a region and does not follow prefecture boundaries; which file holds which part of the prefecture is recorded when it is cut out (`extract_log.json`).
- The numeric-looking columns (作成年度, 植生自然度) are text in the source and kept as such.
- `legend_all_source_raw.tsv` lists every legend; `legend_matches_source_raw.tsv` lists the legends whose name contains ブナ, ミズナラ, ナラ or コナラ, in the original spelling. The match is by substring, so it also catches other species whose names contain these words; nothing was merged.
