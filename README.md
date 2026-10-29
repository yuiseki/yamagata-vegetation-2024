# yamagata-vegetation-2024

Yamagata Prefecture extract of 現存植生図2024 (Biodiversity Center of Japan, Ministry of the Environment),
frozen on Hugging Face as `yuiseki/yamagata-vegetation-2024`. Survey: https://github.com/yuiseki/akita-beech-oak-sources
Same pipeline as `yuiseki/akita-vegetation-2024`, one repository per prefecture (Tohoku: Aomori, Iwate, Miyagi, Akita, Yamagata, Fukushima).

Scripts run in order (`uv run python scripts/NN_*.py`); `data/` is not in git. Tests: `uv run pytest`.

1. `01_download.py` the GeoPackages listed in `scripts/veg.py` (`SOURCE_FILES`) from G空間情報センター and the prefecture boundary (cutter only); `--from-run DIR` (repeatable) reuses GeoPackages of an earlier run after checking their sha256 and the record
2. `02_profile_raw.py`, `03_legend_match.py` raw profile; results in `docs/`
3. `04_extract.py`, `05_profile.py` cut the prefecture and profile it
4. `06_card.py` card, licence, provenance; `07_verify.py` second-engine check against the source
5. `src/publish.py --push` upload in one commit; `08_verify_hub.py` read back at the fixed revision (`docs/revision.md`)
