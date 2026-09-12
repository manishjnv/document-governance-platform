"""Generate every artboard (.dc.html) and canvas.json.

    python gen.py                      # all screens (auto-discovered from screens/*.py)
    python gen.py --only Dashboard,MitreDetail

A screen module exports: STEM, PAGE (one of PAGES ids), TITLE, ORDER (int, layout order within
the page), CLICKS (harness steps) and build(phone) -> [(stem, html)].
"""
import glob
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "screens"))

from dc import write  # noqa: E402

PAGES = [
    ("system", "Shell & system"), ("sow", "SOW & RFP Review"), ("mitre", "MITRE ATT&CK Coverage"),
    ("code", "Code Security Review"), ("admin", "Admin & auth"),
]

W, H, PW, PH, GAP = 1440, 900, 390, 844, 120


def discover():
    mods = []
    for path in sorted(glob.glob(os.path.join(HERE, "screens", "*.py"))):
        name = os.path.basename(path)[:-3]
        if name.startswith("_"):
            continue
        m = importlib.import_module(name)
        if not hasattr(m, "STEM") or not hasattr(m, "build"):
            continue
        mods.append(m)
    order = {p: i for i, (p, _) in enumerate(PAGES)}
    mods.sort(key=lambda m: (order.get(getattr(m, "PAGE", "system"), 99), getattr(m, "ORDER", 50), m.STEM))
    return mods


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    artboards, notes, clicks = [], [], {}
    slot = {p: 0 for p, _ in PAGES}
    for m in discover():
        stem, page, title = m.STEM, getattr(m, "PAGE", "system"), getattr(m, "TITLE", m.STEM)
        if only and stem not in only:
            continue
        i = slot[page]
        y = i * (H + GAP)
        for (s, html) in m.build(False):
            write(HERE, s, html)
            artboards.append({"file": s + ".dc.html", "title": title, "x": 0, "y": y, "w": W, "h": H, "page": page, "expand": "fill", "is_interactive": True})
        for (s, html) in m.build(True):
            write(HERE, s, html)
            artboards.append({"file": s + ".dc.html", "title": title + " · phone", "x": W + 100, "y": y, "w": PW, "h": PH, "page": page, "expand": "fill", "is_interactive": True})
        clicks[stem] = getattr(m, "CLICKS", [])
        labels = [c.get("note") or c.get("text") or c.get("label") for c in getattr(m, "CLICKS", [])]
        labels = [x for x in labels if x]
        if labels:
            txt = "Try on this screen:\n" + "\n".join("· " + x for x in labels)
            notes.append({"id": "n-" + stem.lower(), "x": W + 100 + PW + 60, "y": y, "w": 300, "page": page, "text": txt})
        slot[page] += 1
    if not only:
        canvas = {"pages": [{"id": p, "name": n} for p, n in PAGES], "artboards": artboards, "annotations": notes,
                  "launch": {"view": "canvas", "page": "system"}}
        json.dump(canvas, open(os.path.join(HERE, "canvas.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    old = {}
    cp = os.path.join(HERE, "clicks.json")
    if os.path.exists(cp):
        old = json.load(open(cp, encoding="utf-8"))
    old.update(clicks)
    json.dump(old, open(cp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", len(artboards), "artboards")


if __name__ == "__main__":
    main()
