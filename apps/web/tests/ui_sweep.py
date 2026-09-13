"""Visual sweep of every authenticated route at desktop and phone width.

    python apps/web/tests/ui_sweep.py [--base http://localhost:3000] [--out <dir>] [--routes /a /b]
                                      [--capture-references]

Fails (exit 1) when any page scrolls horizontally (documentElement.scrollWidth > clientWidth)
and prints the offending elements. Writes full-page PNGs per route and viewport to --out.
Needs a running Next dev/prod server and `pip install playwright && playwright install chromium`.
Auth is a placeholder token, so data-driven pages render their error/empty states unless an API
is running and the token is real (pass --token). Same rule as the design harness (RCA #27, #30).
"""
import argparse
import os
import sys

ROUTES = [
    "/login", "/dashboard", "/upload", "/projects/sweep", "/versions/diff?doc_id=a&older=1&newer=2",
    "/results/sweep", "/mitre", "/mitre/new", "/mitre/connections", "/mitre/sweep",
    "/codereview", "/codereview/new", "/codereview/sweep", "/admin",
]
VIEWPORTS = (("desk", 1440, 900), ("phone", 390, 844))
REFERENCES = {  # public pages only; captured into docs/design/references (gitignored)
    "linear": "https://linear.app", "attio": "https://attio.com", "vercel": "https://vercel.com/home",
}
PROBE = """() => { const cw = document.documentElement.clientWidth; const out = [];
  for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect();
    if (r.right > cw + 1 && r.width > 0 && !el.closest('[class*="overflow-x-auto"],[class*="overflow-auto"]'))
      out.push(el.tagName + ' .' + String(el.className || '').slice(0, 80) + ' +' + Math.round(r.right - cw)); }
  return out.slice(0, 8); }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:3000")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", ".sweep"))
    ap.add_argument("--routes", nargs="*", default=ROUTES)
    ap.add_argument("--token", default="sweep")
    ap.add_argument("--capture-references", action="store_true")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright

    os.makedirs(a.out, exist_ok=True)
    failures = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, w, h in VIEWPORTS:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = ctx.new_page()
            pg.goto(a.base + "/login", wait_until="domcontentloaded")
            pg.evaluate("t => { localStorage.setItem('access_token', t); localStorage.setItem('sidebar_collapsed', 'false'); }", a.token)
            for r in a.routes:
                try:
                    pg.goto(a.base + r, wait_until="load", timeout=90000)
                except Exception as e:  # client-side redirects abort navigation; keep going
                    print(f"{name} {r}: goto {str(e).splitlines()[0][:60]}")
                pg.wait_for_timeout(1500)
                stem = r.strip("/").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_") or "home"
                pg.screenshot(path=os.path.join(a.out, f"{stem}-{name}.png"), full_page=True)
                over = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
                status = "OK" if over <= 0 else f"OVERFLOW +{over}px"
                print(f"{name:5} {r:45} {status}")
                if over > 0:
                    failures.append((name, r, over))
                    for line in pg.evaluate(PROBE):
                        print("        ", line)
            ctx.close()
        if a.capture_references:
            ref_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "design", "references")
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            pg = ctx.new_page()
            for key, url in REFERENCES.items():
                try:
                    pg.goto(url, wait_until="load", timeout=60000)
                    pg.wait_for_timeout(2000)
                    pg.screenshot(path=os.path.join(ref_dir, f"{key}.png"), full_page=False)
                    print("reference", key, "captured")
                except Exception as e:
                    print("reference", key, "failed:", str(e).splitlines()[0][:60])
            ctx.close()
        b.close()
    print("sweep:", "OK" if not failures else f"{len(failures)} page(s) overflow")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
