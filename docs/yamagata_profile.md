# Yamagata extract of 現存植生図2024: verification and profile

- polygons: 141,922 (141,922 MultiPolygon), CRS EPSG:6668, bbox lon 139.5200 to 140.6465, lat 37.7338 to 39.2155
- source files: {'veg2024bk2a.gpkg': 127057, 'veg2024bk4.gpkg': 10216, 'veg2024bk2b.gpkg': 4649}
- cut: 140,369 polygons wholly inside Yamagata kept as they are; 1,553 polygons that cross the boundary were clipped to it (none dropped); the clipped polygons had 1657.3 km2 before the cut and keep 533.1 km2
- area: 9327.726 km2 in EPSG:6678, against 9327.707 km2 for the N03 polygon of Yamagata (100.00020%, difference +0.018 km2)
- area by 地域ブロック: 2 東北 8706.210 km2 (93.34% of N03), 4 北陸 621.516 km2 (6.66% of N03)
- geometry validity: 0 invalid, 0 empty; fid unique: True
- overlaps: 831 pairs of polygons overlap by a sliver (largest 1.59e-07 square degrees, about 1541 m2); not repaired
- NULLs: 0 in all columns

## 作成年度 (polygons)

| year | polygons |
| --- | ---: |
| 2000 | 22,592 |
| 2001 | 13,811 |
| 2003 | 671 |
| 2012 | 7,835 |
| 2013 | 10,983 |
| 2015 | 26,084 |
| 2017 | 26,948 |
| 2018 | 575 |
| 2020 | 32,423 |

## Legends whose name contains ブナ, ミズナラ, ナラ or コナラ

11 of the 136 legends present in Yamagata; 26,257 polygons, 4046.0 km2 together (the legends overlap in meaning, do not read this as one class).

| code | name (original) | polygons | area km2 | ブナ | ミズナラ | ナラ | コナラ |
| --- | --- | ---: | ---: | :-: | :-: | :-: | :-: |
| 110100 | チシマザサ－ブナ群団 | 3,932 | 1200.41 | x |  |  |  |
| 110103 | スギ－ブナ群落 | 336 | 15.07 | x |  |  |  |
| 110501 | ホツツジ－ミズナラ群集 | 1,150 | 33.45 |  | x | x |  |
| 190100 | ウラジロヨウラク－ミヤマナラ群団 | 642 | 37.72 |  |  | x |  |
| 190101 | ミヤマナラ群落 | 1,921 | 91.26 |  |  | x |  |
| 220100 | ブナ－ミズナラ群落 | 3,175 | 1112.21 | x | x | x |  |
| 220103 | オオバクロモジ－ミズナラ群集 | 3,727 | 619.99 |  | x | x |  |
| 220104 | ブナ二次林 | 64 | 5.61 | x |  |  |  |
| 220500 | コナラ群落（V） | 8 | 0.19 |  |  | x | x |
| 220501 | オクチョウジザクラ－コナラ群集 | 11,283 | 929.17 |  |  | x | x |
| 410101 | クリ－コナラ群集 | 19 | 0.93 |  |  | x | x |

The match is by substring on the original name. ナラ also matches names that are neither ミズナラ nor コナラ: ウラジロヨウラク－ミヤマナラ群団 (190100), ミヤマナラ群落 (190101).
The full list of Yamagata legends is `legend_yamagata.tsv`.

## 作成年度 of the polygons of those legends

| year | polygons |
| --- | ---: |
| 2000 | 3,733 |
| 2001 | 1,857 |
| 2003 | 144 |
| 2012 | 1,454 |
| 2013 | 2,281 |
| 2015 | 5,259 |
| 2017 | 5,040 |
| 2018 | 192 |
| 2020 | 6,297 |
