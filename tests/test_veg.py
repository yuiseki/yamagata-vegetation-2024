import numpy as np
import pytest
import shapely
import veg
from shapely.geometry import MultiPolygon, box


def test_prefs_cover_the_six_tohoku_prefectures():
    assert set(veg.PREFS) == {"aomori", "iwate", "miyagi", "akita", "yamagata", "fukushima"}
    assert [veg.PREFS[k]["code"] for k in ("aomori", "iwate", "miyagi", "akita", "yamagata", "fukushima")] == [
        "02", "03", "04", "05", "06", "07",
    ]  # fmt: skip


def test_zone_of_fukushima_is_ix_and_the_rest_x():
    assert veg.PREFS["fukushima"]["crs"] == 6677
    assert all(veg.PREFS[k]["crs"] == 6678 for k in ("aomori", "iwate", "miyagi", "akita", "yamagata"))


@pytest.mark.parametrize("slug", sorted(veg.PREFS))
def test_n03_url_names_the_prefecture_code(slug):
    url = veg.n03_url(slug)
    assert url.endswith(f"N03-20260101_{veg.PREFS[slug]['code']}_GML.zip")
    assert url.startswith("https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2026/")


def test_n03_names_are_the_prefecture_names():
    assert veg.PREFS["fukushima"]["ja"] == "福島県" and veg.PREFS["aomori"]["ja"] == "青森県"


def test_classify_and_clip():
    cutter = box(0, 0, 10, 10)
    inside = box(1, 1, 2, 2)
    crossing = box(9, 9, 12, 12)
    touching = box(10, 0, 12, 5)  # shares an edge only
    outside = box(20, 20, 21, 21)
    g = np.array([inside, crossing, touching, outside])
    ins, cross = veg.classify(g, cutter)
    assert ins.tolist() == [True, False, False, False]
    assert cross.tolist() == [False, True, True, False]  # the edge-sharing one intersects
    pieces = veg.clip_crossing(g[cross], cutter)
    assert pieces[0].area == pytest.approx(1.0)
    assert pieces[1] is None  # an edge has no area, so it is dropped
    assert isinstance(pieces[0], MultiPolygon)


def test_polygons_of_drops_lines_and_points():
    mixed = shapely.GeometryCollection([box(0, 0, 1, 1), shapely.LineString([(0, 0), (1, 1)])])
    out = veg.polygons_of(mixed)
    assert out.geom_type == "MultiPolygon" and out.area == 1.0
    assert veg.polygons_of(shapely.LineString([(0, 0), (1, 1)])) is None
    assert veg.polygons_of(None) is None


def test_size_category_edges():
    assert veg.size_category(999) == "n<1K"
    assert veg.size_category(174_576) == "100K<n<1M"
    assert veg.size_category(99_999) == "10K<n<100K"


def _row(code, name, **flags):
    r = {"凡例コード": code, "凡例名": name}
    r |= {f"has_{w}": flags.get(w, False) for w in veg.WORDS}
    return r


def test_match_notes_flag_other_oaks():
    rows = [
        _row("1", "ブナ群落", ブナ=True),
        _row("2", "ミズナラ群落", ミズナラ=True, ナラ=True),
        _row("3", "ミヤマナラ群落", ナラ=True),
        _row("4", "イヌブナ群落", ブナ=True),
    ]
    notes = veg.match_notes(rows)
    assert any("ミヤマナラ群落 (3)" in n and "ミズナラ群落" not in n for n in notes)
    assert any("イヌブナ群落 (4)" in n and "ブナ群落 (1)" not in n for n in notes)
    assert veg.match_notes([_row("1", "ブナ群落", ブナ=True)]) == []


def test_no_script_carries_a_prefecture_name_of_its_own():
    """The scripts are shared by all prefecture repositories; names come from veg.PREFS only."""
    from pathlib import Path

    root = Path(__file__).parents[1]
    names = [v["ja"] for v in veg.PREFS.values()] + [v["en"] for v in veg.PREFS.values()]
    names += [v["ja"][:-1] for v in veg.PREFS.values()]
    for f in [*root.glob("scripts/*.py"), *root.glob("src/*.py")]:
        if f.name == "veg.py":
            continue
        text = f.read_text(encoding="utf-8")
        found = [n for n in names if n in text]
        assert not found, (f.name, found)


def test_source_files_are_known_block_files_and_tohoku_is_always_listed_first_or_by_need():
    known = {f"veg2024bk{n}{s}.gpkg" for n in range(1, 9) for s in ("", "a", "b")}
    for slug, c in veg.PREFS.items():
        assert c["files"] and set(c["files"]) <= known, slug
        assert len(set(c["files"])) == len(c["files"]), slug
    assert veg.PREFS["fukushima"]["files"] == ["veg2024bk2a.gpkg", "veg2024bk3.gpkg", "veg2024bk4.gpkg"]
    assert "veg2024bk4.gpkg" in veg.PREFS["yamagata"]["files"]
    for slug in ("aomori", "iwate", "miyagi", "akita"):
        assert veg.PREFS[slug]["files"] == veg.TOHOKU_FILES


def test_block_names_cover_the_eight_blocks():
    assert sorted(veg.BLOCK_NAMES) == [str(i) for i in range(1, 9)]
    assert veg.BLOCK_NAMES["4"] == "北陸"
