"""Render + interaction harness, standalone (no editor).

The editor mounts artboard iframes lazily and unreliably headless, so this renders each artboard
directly with the same runtime the editor uses: React, ReactDOM and support.js extracted from the
payload (see extract_runtime.py in the scratchpad; set DC_RUNTIME to the folder holding
reactUmd.js, reactDomUmd.js, supportJs.js). The artboard's `<script src="./support.js">` tag is
replaced by the three script tags, exactly as the editor's own export zip lays them out.

    python harness.py --screens Main,CodeReviewList [--phone] [--out DIR]
Checks per screen: mounted (data-ready), no {{ leak, no console/page errors after ready,
no horizontal overflow, scripted CLICKS from clicks.json, screenshot.
"""
import http.server
import json
import os
import shutil
import socketserver
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.environ.get("DC_RUNTIME", os.path.join(os.path.dirname(HERE), "..", "..", "_dc_runtime"))
TAG = '<script src="./support.js"></script>'
REPL = '<script src="./vendor-react.js"></script>\n<script src="./vendor-react-dom.js"></script>\n<script src="./support.js"></script>'


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory):
    handler = lambda *a, **k: Quiet(*a, directory=directory, **k)
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def stage(stem, outdir):
    """Copy the artboard + runtime into outdir as a standalone page."""
    src = open(os.path.join(HERE, stem + ".dc.html"), encoding="utf-8").read()
    assert TAG in src, "support.js tag missing in " + stem
    open(os.path.join(outdir, stem + ".html"), "w", encoding="utf-8").write(src.replace(TAG, REPL, 1))
    for a, b in (("reactUmd.js", "vendor-react.js"), ("reactDomUmd.js", "vendor-react-dom.js"), ("supportJs.js", "support.js")):
        shutil.copy(os.path.join(RUNTIME, a), os.path.join(outdir, b))


def run(stems, phone, outdir):
    from playwright.sync_api import sync_playwright
    os.makedirs(outdir, exist_ok=True)
    clicks_all = json.load(open(os.path.join(HERE, "clicks.json"), encoding="utf-8"))
    srv, port = serve(outdir)
    results = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for stem in stems:
            stage(stem, outdir)
            vw = (430, 900) if phone else (1500, 950)
            pg = b.new_page(viewport={"width": vw[0], "height": vw[1]})
            errs, ready_at = [], None
            pg.on("pageerror", lambda e: errs.append(("pageerror", str(e)[:220], time.time())))
            pg.on("console", lambda m: errs.append(("console", m.text[:220], time.time())) if m.type == "error" else None)
            pg.goto("http://127.0.0.1:%d/%s.html" % (port, stem))
            root = pg.locator('[data-screen="%s"][data-ready="1"]' % stem)
            mounted = False
            try:
                root.first.wait_for(timeout=25000)
                mounted = True
                ready_at = time.time()
            except Exception:
                pass
            res = {"mounted": mounted, "leak": None, "overflow": None, "clicks": []}
            if mounted:
                time.sleep(0.6)
                html = pg.content()
                res["leak"] = "{{" in html
                res["overflow"] = pg.evaluate("""() => { const w = document.documentElement.clientWidth; const scr = (e) => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if ((o === 'auto' || o === 'scroll') && p.getBoundingClientRect().right <= w + 1) return true; } return false; };
                    for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect();
                      if (r.right > w + 1 && r.width > 0 && r.width < 3000 && getComputedStyle(el).position !== 'fixed' && !el.closest('.sheet,.msheet,.dlg-ov,.ov,.side') && !scr(el)) return true; }
                    return false; }""")
                res["page_width"] = pg.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                if res["page_width"][0] > res["page_width"][1] + 1:
                    res["overflow"] = True  # the page itself scrolls sideways (hidden tooltips did this once)
                if res["overflow"]:
                    res["overflow_culprits"] = pg.evaluate("""() => { const w = document.documentElement.clientWidth; const out = []; const scr = (e) => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if ((o === 'auto' || o === 'scroll') && p.getBoundingClientRect().right <= w + 1) return true; } return false; };
                        for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect(); if (r.right > w + 1 && r.width > 0 && r.width < 3000) {
                          const cs = getComputedStyle(el); if (cs.position === 'fixed' || el.closest('.sheet,.msheet,.dlg-ov,.ov,.side') && !scr(el)) continue;
                          out.push((el.tagName.toLowerCase()) + '.' + String(el.className).split(' ').slice(0,2).join('.') + ' right=' + Math.round(r.right)); if (out.length >= 8) break; } }
                        return out; }""")
                base = stem[:-5] if stem.endswith("Phone") else stem
                for step in clicks_all.get(base, []):
                    if phone and step.get("desktop_only"):
                        res["clicks"].append({"step": step, "ok": True, "skipped": "desktop_only"})
                        continue
                    try:
                        if "label" in step or "text" in step or "css" in step:
                            if "css" in step:
                                loc = pg.locator(step["css"])
                            elif "label" in step:
                                loc = pg.get_by_label(step["label"], exact=True)
                            else:
                                loc = pg.get_by_text(step["text"], exact=True)
                            loc = loc.nth(step.get("nth", 0)) if "nth" in step else loc.locator("visible=true").first
                            loc.click(timeout=4000)
                        if "expect" in step:
                            pg.get_by_text(step["expect"]).first.wait_for(timeout=4000)
                        if "check" in step:
                            ok = False
                            for _ in range(20):
                                if pg.evaluate("() => !!(%s)" % step["check"]):
                                    ok = True
                                    break
                                time.sleep(0.15)
                            if not ok:
                                raise RuntimeError("check failed: " + step["check"])
                        res["clicks"].append({"ok": True, "step": step})
                    except Exception as e:
                        res["clicks"].append({"ok": False, "step": step, "err": str(e).splitlines()[0][:160]})
                try:
                    pg.screenshot(path=os.path.join(outdir, "%s.png" % stem), full_page=not phone)
                except Exception as e:
                    res["shot_err"] = str(e)[:120]
            res["errors_after_ready"] = [e[1] for e in errs if ready_at and e[2] > ready_at]
            res["errors_before_ready"] = [e[1] for e in errs if not ready_at or e[2] <= ready_at][:3]
            results[stem] = res
            pg.close()
        b.close()
    srv.shutdown()
    return results


if __name__ == "__main__":
    stems = sys.argv[sys.argv.index("--screens") + 1].split(",") if "--screens" in sys.argv else []
    phone = "--phone" in sys.argv
    outdir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(HERE, "_out")
    r = run([s + ("Phone" if phone else "") for s in stems], phone, outdir)
    bad = 0
    for k, v in r.items():
        ok = v["mounted"] and not v["leak"] and not v["errors_after_ready"] and not v["overflow"] and all(c["ok"] for c in v["clicks"])
        bad += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + k, json.dumps({x: y for x, y in v.items() if x != "clicks"}, ensure_ascii=False)[:600],
              "clicks:", ["ok" if c["ok"] else ("FAIL " + json.dumps(c["step"], ensure_ascii=False) + " " + c.get("err", "")) for c in v["clicks"]])
    sys.exit(1 if bad else 0)
