"""Constants and helpers shared by the scripts of this repository.

PREF is the only line that differs between the prefecture repositories (`<slug>-vegetation-2024`).
"""

import numpy as np
import shapely

PREF = "yamagata"  # SLUG-LINE

CKAN_ID = "biodic_veg2024"
CKAN_URL = f"https://www.geospatial.jp/ckan/api/3/action/package_show?id={CKAN_ID}"
PAGE_URL = f"https://www.geospatial.jp/ckan/dataset/{CKAN_ID}"
BIODIC_PAGE_URL = "https://www.biodic.go.jp/kiso/vg/vg_kiso.html"
STORY_URL = (
    "https://pl-moej.gisservice.jp/arcgis/apps/storymaps/stories/a366ce0b9e674e46872baac1ab34eb13"
)
LICENSE_ID = "public-data-license-v1.0"
PDL_URL = "https://www.digital.go.jp/resources/open_data/public_data_license_v1.0"
UA = "Mozilla/5.0 (research; yuiseki)"
# The publisher splits the map into blocks (地域ブロック: 1 北海道, 2 東北, 3 関東, 4 北陸, ...); the Tohoku
# block is two files, a and b. A block is a region of its own and does not follow prefecture boundaries.
TOHOKU_FILES = ["veg2024bk2a.gpkg", "veg2024bk2b.gpkg"]
BLOCK_NAMES = {"1": "北海道", "2": "東北", "3": "関東", "4": "北陸", "5": "中部", "6": "近畿", "7": "中四国", "8": "九州沖縄"}
N03_PAGE_URL = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-2026.html"
N03_URL_FMT = "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2026/N03-20260101_{code}_GML.zip"

# files: the source files that hold parts of the prefecture. Aomori, Iwate and Miyagi are covered by the two
# Tohoku files (the stored polygons add up to 100% of the N03 area). Parts of Yamagata (Asahi and Iide
# mountains, 621 km2) and Fukushima (Tadami and the border with Niigata, Gunma, Tochigi and Ibaraki, 489 km2)
# lie in the neighbouring Hokuriku (bk4) and Kanto (bk3) blocks; that was found by cutting the Tohoku files
# alone and comparing the area with N03, then intersecting those two blocks with the prefecture.
# code: JIS X 0401 prefecture code (the N03 file name), ja: the value of N03_001,
# crs: JGD2011 / Japan Plane Rectangular CS of the prefecture (zone X = 6678 covers Aomori, Akita,
# Yamagata, Iwate and Miyagi; zone IX = 6677 covers Fukushima), used only for areas.
PREFS = {
    "aomori": {"code": "02", "ja": "青森県", "en": "Aomori", "crs": 6678, "files": TOHOKU_FILES},
    "iwate": {"code": "03", "ja": "岩手県", "en": "Iwate", "crs": 6678, "files": TOHOKU_FILES},
    "miyagi": {"code": "04", "ja": "宮城県", "en": "Miyagi", "crs": 6678, "files": TOHOKU_FILES},
    "akita": {"code": "05", "ja": "秋田県", "en": "Akita", "crs": 6678, "files": TOHOKU_FILES},
    "yamagata": {"code": "06", "ja": "山形県", "en": "Yamagata", "crs": 6678, "files": [*TOHOKU_FILES, "veg2024bk4.gpkg"]},
    "fukushima": {"code": "07", "ja": "福島県", "en": "Fukushima", "crs": 6677, "files": ["veg2024bk2a.gpkg", "veg2024bk3.gpkg", "veg2024bk4.gpkg"]},
}
ATTRS = ["植生区分コード", "大区分コード", "中区分コード", "細区分コード", "凡例コード", "凡例名",
         "植生自然度", "植生自然度区分", "植生区分", "作成年度", "地域ブロック"]  # fmt: skip
WORDS = ["ブナ", "ミズナラ", "ナラ", "コナラ"]
UNCUT_COLUMNS = ["fid", *ATTRS, "source_file", "clipped", "source_area_m2", "area_m2", "geometry"]


def conf(slug: str = PREF) -> dict:
    return {"slug": slug, **PREFS[slug]}


CODE = PREFS[PREF]["code"]
JA = PREFS[PREF]["ja"]
EN = PREFS[PREF]["en"]
AREA_CRS = PREFS[PREF]["crs"]
SOURCE_FILES = PREFS[PREF]["files"]
REPO = f"{PREF}-vegetation-2024"
PARQUET = f"vegetation_{PREF}.parquet"
N03_ZIP = f"N03-20260101_{CODE}_GML.zip"
N03_URL = N03_URL_FMT.format(code=CODE)


def n03_url(slug: str) -> str:
    return N03_URL_FMT.format(code=PREFS[slug]["code"])


def polygons_of(geom):
    """The polygonal part of a geometry as one MultiPolygon, or None when no part has an area."""
    if geom is None or geom.is_empty:
        return None
    parts = [p for p in shapely.get_parts(geom) if p.geom_type == "Polygon" and p.area > 0]
    return shapely.multipolygons(parts) if parts else None


def classify(geoms, cutter) -> tuple[np.ndarray, np.ndarray]:
    """(inside, cross) masks: inside = wholly in the cutter, cross = intersects but not wholly in."""
    hit = shapely.intersects(geoms, cutter)
    inside = shapely.contains(cutter, geoms)
    return inside, hit & ~inside


def clip_crossing(geoms, cutter) -> list:
    """Each crossing geometry clipped to the cutter; None where nothing with an area is left."""
    return [polygons_of(x) for x in shapely.intersection(geoms, cutter)]


def size_category(n: int) -> str:
    for hi, label in [(1_000, "n<1K"), (10_000, "1K<n<10K"), (100_000, "10K<n<100K"),
                      (1_000_000, "100K<n<1M"), (10_000_000, "1M<n<10M")]:  # fmt: skip
        if n < hi:
            return label
    return "n>10M"


def match_notes(hit_rows: list[dict]) -> list[str]:
    """Plain-language notes on the legends that matched by substring, from the rows themselves.
    A row has 凡例コード, 凡例名 and a has_<word> flag for each search word."""
    notes = []
    only_nara = [r for r in hit_rows if r["has_ナラ"] and not r["has_ミズナラ"] and not r["has_コナラ"]]
    if only_nara:
        names = ", ".join(f"{r['凡例名']} ({r['凡例コード']})" for r in only_nara)
        notes.append(f"ナラ also matches names that are neither ミズナラ nor コナラ: {names}.")
    inu = [r for r in hit_rows if "イヌブナ" in r["凡例名"]]
    if inu:
        names = ", ".join(f"{r['凡例名']} ({r['凡例コード']})" for r in inu)
        notes.append(f"ブナ also matches イヌブナ, another species: {names}.")
    return notes
