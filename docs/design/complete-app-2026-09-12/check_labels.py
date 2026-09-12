"""Static completeness check: every verbatim string in labels.json must appear in its screen's artboard.

    python check_labels.py            # exit 1 on any MISSING
"""
import html as H
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    s = H.unescape(s)
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"').replace("…", "...").replace(" ", " ")
    s = s.replace("\\u2019", "'")
    return re.sub(r"\s+", " ", s).strip()


def main():
    labels = json.load(open(os.path.join(HERE, "labels.json"), encoding="utf-8"))
    import glob
    for extra in sorted(glob.glob(os.path.join(HERE, "labels", "*.json"))):
        stem = os.path.basename(extra)[:-5]
        labels.setdefault(stem, [])
        labels[stem] = list(dict.fromkeys(labels[stem] + json.load(open(extra, encoding="utf-8"))))
    shell = labels.pop("_shell", [])
    missing = 0
    for stem, items in labels.items():
        path = os.path.join(HERE, stem + ".dc.html")
        if not os.path.exists(path):
            print("SKIP %s (not generated yet)" % stem)
            continue
        raw = open(path, encoding="utf-8").read()
        hay_raw = norm(raw)
        hay_txt = norm(re.sub(r"<[^>]+>", " ", raw))
        has_shell = 'aria-label="Sidebar"' in raw
        for lab in (shell if has_shell else []) + items:
            n = norm(lab)
            if n not in hay_raw and n not in hay_txt:
                print('MISSING %s: "%s"' % (stem, lab))
                missing += 1
    print("labels check:", "OK" if missing == 0 else "%d missing" % missing)
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
