"""Bundle cached constellations into docs/data.js for the static GitHub Pages showcase."""
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE / "docs"

# Display order for the gallery (only those with a cached constellation are included).
ORDER = [
    "N17G0Mw43YA",  # Pauline Hanson — National Press Club
    "D9Ihs241zeg",  # Chimamanda Ngozi Adichie — The danger of a single story
    "iG9CE55wbtY",  # Sir Ken Robinson — Do schools kill creativity?
    "TMrtLsQbaok",  # Greta Thunberg — How dare you
]

data, order = {}, []
for vid in ORDER:
    f = CACHE / f"{vid}.json"
    if f.exists():
        try:
            data[vid] = json.loads(f.read_text())
            order.append(vid)
        except Exception as e:
            print(f"skip {vid}: {e}")

DOCS.mkdir(exist_ok=True)
js = ("window.CONSTELLATIONS = " + json.dumps(data, ensure_ascii=False) + ";\n"
      "window.ORDER = " + json.dumps(order) + ";\n")
(DOCS / "data.js").write_text(js, encoding="utf-8")
print(f"wrote docs/data.js with {len(order)} constellations: {order}")
