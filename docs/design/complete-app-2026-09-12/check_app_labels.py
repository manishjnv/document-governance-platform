"""Check that a screen's required UI strings are still present in the app's TSX sources.

    python check_app_labels.py <Stem|_shell> <tsx path> [<tsx path> ...]     # exit 1 on a miss

The lists in labels.json / labels/<Stem>.json were generated from the code inventory, so a miss
means a string was dropped or changed during the restyle.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_labels import norm  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    stem, paths = sys.argv[1], sys.argv[2:]
    labels = json.load(open(os.path.join(HERE, "labels.json"), encoding="utf-8"))
    items = list(labels.get(stem, []))
    extra = os.path.join(HERE, "labels", stem + ".json")
    if os.path.exists(extra):
        items = list(dict.fromkeys(items + json.load(open(extra, encoding="utf-8"))))
    if not items:
        print("unknown stem %s" % stem)
        sys.exit(2)
    raw = "\n".join(open(p, encoding="utf-8").read() for p in paths).replace("\'", "'")
    hay_raw = norm(raw)
    txt = re.sub(r"\{\s*['\"] ['\"]\s*\}", " ", raw)          # {' '} / {" "}
    txt = re.sub(r"\{/\*.*?\*/\}", " ", txt, flags=re.S)      # {/* comments */}
    txt = re.sub(r"<[^>]+>", " ", txt)                        # tags
    hay_txt = norm(txt)
    missing = 0
    for lab in items:
        n = norm(lab)
        if n not in hay_raw and n not in hay_txt:
            print('MISSING %s: "%s"' % (stem, lab))
            missing += 1
    print("labels check %s: %s" % (stem, "OK (%d strings)" % len(items) if not missing else "%d missing" % missing))
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
