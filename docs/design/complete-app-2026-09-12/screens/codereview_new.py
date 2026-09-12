"""/codereview/new — New code security review: get scanner + upload results. Source: inventory §A2."""
from dc import T, app_shell, screen, chip, icon, dropzone, filerow

STEM = "CodeReviewNew"
PAGE, TITLE, ORDER = "code", "New code security review", 20

DATA = {}

STEPROW = '<div class="row" style="gap:10px;align-items:flex-start"><span style="flex:none;width:20px;height:20px;border-radius:999px;background:var(--accent-soft);color:var(--accent);font-size:11px;font-weight:600;display:flex;align-items:center;justify-content:center;margin-top:1px">%s</span><span style="font-size:13px;line-height:1.6;color:var(--ink2)">%s</span></div>'

STEP1 = STEPROW % ("1", 'Unzip the kit, then run <code class="code">.\\setup.cmd</code> (Windows, double-click works) or <code class="code">setup.sh</code> (macOS/Linux) — it installs the scanner and asks for your OpenRouter key')
STEP2 = STEPROW % ("2", 'Run <code class="code">.\\scopewise-scan.cmd &lt;repo&gt;</code> / <code class="code">scopewise-scan.sh &lt;repo&gt;</code> — shows the cost estimate, then scans after you confirm')
STEP3 = STEPROW % ("3", 'Upload the <code class="code">scopewise-scan-*.zip</code> it produces here')

CARD1 = T("""
<div class="card">
  <div class="card-h"><h3>1 · Get the scanner</h3>[[pill]]</div>
  <div class="card-b stack" style="gap:14px">
    <div>
      <button class="btn primary tip" data-tip="[[dltip]]" onClick="{{dlKit}}">
        <sc-if value="{{dlBusy}}" hint-placeholder-val="{{false}}">[[spin]]</sc-if><sc-if value="{{dlIdle}}" hint-placeholder-val="{{true}}">[[dlicon]]</sc-if>
        Download scan kit
      </button>
      <div class="faint" style="font-size:11px;margin-top:6px">Saves scopewise-scan-kit-v1.3.0.zip</div>
      <sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><p class="err-line" role="alert" style="margin-top:6px">Could not download the scan kit</p></sc-if>
    </div>
    <div class="stack" style="gap:12px">[[s1]][[s2]][[s3]]</div>
    <div class="row" style="gap:10px;align-items:center"><hr class="hr" style="flex:1"><span class="faint" style="font-size:12px;white-space:nowrap">or run VVAH directly</span><hr class="hr" style="flex:1"></div>
    <div class="row" style="align-items:flex-start;gap:8px">
      <pre class="block mono grow" style="margin:0">vvaharness scan --repo /path/to/repo --stop-after s9</pre>
      <button class="btn icon tip" aria-label="Copy command" data-tip="Copy command" onClick="{{copyCmd}}">
        <sc-if value="{{copied}}" hint-placeholder-val="{{false}}">[[check]]</sc-if><sc-if value="{{notCopied}}" hint-placeholder-val="{{true}}">[[copy]]</sc-if>
      </button>
    </div>
    <sc-if value="{{copied}}" hint-placeholder-val="{{false}}"><span class="chip ok xs" style="align-self:flex-start">Copied</span></sc-if>
    <div style="font-size:13px"><a href="https://github.com/visa/visa-vulnerability-agentic-harness" target="_blank" rel="noopener noreferrer">Visa Vulnerability Agentic Harness</a></div>
    <div class="row" style="gap:8px;align-items:flex-start;font-size:12px;color:var(--ink2)">[[info]]<span>Findings are AI triage candidates from your scan; nothing runs on ScopeWise.</span></div>
  </div>
</div>""", pill=chip("VVAH v1.3.0", "info", tip="Pinned Visa Vulnerability Agentic Harness release inside the kit"),
             dltip="Zip with the scanner, setup + run scripts and README (~1 MB). Unzip it, do not pip install it.",
             spin=icon("loader", 15, cls="spin"), dlicon=icon("download", 15), s1=STEP1, s2=STEP2, s3=STEP3,
             check=icon("check", 15), copy=icon("copy", 15), info=icon("info", 14))

CARD2 = T("""
<div class="card">
  <div class="card-h"><h3>2 · Upload the results</h3></div>
  <div class="card-b stack" style="gap:14px">
    <div><label class="label">Name <span class="faint" style="font-weight:400">(optional)</span></label>
      <input id="review-name" class="input" style="width:100%" placeholder="e.g. Q3 backend security scan" value="{{name}}" onChange="{{setName}}"></div>
    <div>
      <sc-if value="{{drop.scan.none}}" hint-placeholder-val="{{true}}">[[dz]]</sc-if>
      <sc-if value="{{drop.scan.has}}" hint-placeholder-val="{{false}}">[[fr]]</sc-if>
      <sc-if value="{{is.error}}" hint-placeholder-val="{{false}}">
        <p class="err-line" role="alert" style="margin-top:6px">Scan report: only .json, .sarif, .zip files are supported</p>
        <p class="err-line" role="alert" style="margin-top:4px">Scan report: file must be under 10 MB</p>
      </sc-if>
    </div>
    <div>
      <sc-if value="{{drop.manifest.none}}" hint-placeholder-val="{{true}}"><button class="btn" style="width:100%;border-style:dashed;justify-content:center" onClick="{{addManifest}}">+ Add run_manifest_*.json (optional)</button></sc-if>
      <sc-if value="{{drop.manifest.has}}" hint-placeholder-val="{{false}}">[[frm]]</sc-if>
      <sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><p class="err-line" role="alert" style="margin-top:6px">Run manifest: only .json files are supported</p></sc-if>
    </div>
    <sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><p class="err-line" role="alert">Please add your findings.json, .sarif or scan zip file first</p></sc-if>
    <div>
      <button class="btn primary {{submitCls}}" style="width:100%;height:40px;justify-content:center" onClick="{{submit}}"><sc-if value="{{submitBusy}}" hint-placeholder-val="{{false}}">[[spin]]</sc-if>{{submitLabel}}</button>
      <sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><p class="err-line" role="alert" style="margin-top:6px">Upload failed</p></sc-if>
    </div>
  </div>
</div>""", dz=dropzone("scan", "Drag &amp; drop or click to select", "findings.json, .sarif or the scan zip · up to 10 MB", "Scan report: choose a file or drag it here"),
             fr=filerow("scan", "drop.scan.removeAria"), frm=filerow("manifest", "drop.manifest.removeAria"), spin=icon("loader", 14, cls="spin"))

BODY = T("""
<div class="pagehead"><div class="row" style="gap:8px"><span style="color:var(--accent)">[[bug]]</span><h1>New code security review</h1></div></div>
<div class="grid g2" style="gap:16px;align-items:start;max-width:920px">[[c1]][[c2]]</div>
""", bug=icon("bug", 18), c1=CARD1, c2=CARD2)

VALS = r"""
const dropScan = self.dropVals('scan', 'scopewise-scan-nodegoat.zip', '1.8 MB');
const dropMan = self.dropVals('manifest', 'run_manifest_nodegoat.json', '3 KB');
const submitBusy = self.busy('submit');
const hasFile = dropScan.has;
return {
  dlBusy: self.busy('dl'), dlIdle: !self.busy('dl'),
  dlKit: (e) => { e.stopPropagation(); self.runBusy('dl', 1100); },
  copied: self.busy('copyCmd'), notCopied: !self.busy('copyCmd'),
  copyCmd: (e) => { e.stopPropagation(); self.runBusy('copyCmd', 1500); },
  drop: { scan: Object.assign(dropScan, { removeAria: 'Remove ' + (dropScan.file || '') }),
          manifest: Object.assign(dropMan, { removeAria: 'Remove ' + (dropMan.file || '') }) },
  addManifest: (e) => { e.stopPropagation(); dropMan.pick(e); },
  name: S.reviewName || '', setName: e => self.setState({ reviewName: e.target.value }),
  submitBusy, submitCls: (!hasFile || submitBusy) ? 'disabled' : '',
  submitLabel: submitBusy ? 'Parsing…' : 'Import and review →',
  submit: (e) => { e.stopPropagation(); if (!hasFile || submitBusy) return; self.runBusy('submit', 1400); }
};
"""

CLICKS = [
    {"text": "Download scan kit", "check": "document.querySelector('.spin') !== null"},
    {"label": "Scan report: choose a file or drag it here", "check": "document.querySelectorAll('.filerow').length === 1"},
    {"text": "+ Add run_manifest_*.json (optional)", "check": "document.querySelectorAll('.filerow').length === 2"},
    {"label": "Copy command", "check": "document.body.textContent.includes('Copied')"},
    {"text": "Import and review →", "check": "document.body.textContent.includes('Parsing')"},
    {"label": "Remove scopewise-scan-nodegoat.zip", "check": "document.querySelectorAll('.filerow').length === 1"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    props = {"view": {"editor": "enum", "options": ["default", "error"], "default": "default", "section": "State"}}
    html = screen(stem, app_shell("codereview", BODY), VALS, DATA, {}, props=props, phone=phone)
    return [(stem, html)]
