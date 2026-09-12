"""/upload — Upload document (new) / Upload new version. Source: inventory/sow.md §2."""
from dc import T, app_shell, screen, chip, icon, dropzone, filerow

STEM = "Upload"
PAGE, TITLE, ORDER = "sow", "Upload document", 20

DATA = {"projects": ["NovaRetail Software Solutions", "ConflictTest", "RFPValidation", "Acme"]}

PROJECT_FIELD = T("""<div>
<label class="label">Project <span class="req">*</span></label>
<sc-if value="{{proj.preset}}" hint-placeholder-val="{{true}}">
  <div class="row" style="gap:8px">[[chip]]<button class="btn sm" onClick="{{proj.change}}">Change</button></div>
</sc-if>
<sc-if value="{{proj.free}}" hint-placeholder-val="{{false}}">
  <input class="input" style="width:100%" list="upload-projects" placeholder="Select existing or type a new project name" value="{{proj.value}}" onChange="{{proj.setValue}}">
  <p class="faint" style="font-size:12px;margin-top:6px">Pick an existing project from the list, or type a new name to create one.</p>
</sc-if>
<datalist id="upload-projects"><sc-for list="{{projects}}" as="p" hint-placeholder-count="4"><option value="{{p}}"></option></sc-for></datalist>
</div>""", chip=chip("{{proj.name}}", "grey"))

DROPZONE = T("""<div>
<sc-if value="{{drop.dz.none}}" hint-placeholder-val="{{true}}">[[dz]]</sc-if>
<sc-if value="{{drop.dz.has}}" hint-placeholder-val="{{false}}">
  <div class="row" style="gap:8px;align-items:center"><span style="font-size:13px;font-weight:600">Selected:</span><div class="grow">[[fr]]</div></div>
</sc-if>
</div>""", dz=dropzone("dz", "Drag and drop your document", "or click to select<br>PDF, DOCX, DOC, XLSX, XLS, or CSV • up to 50MB", "Choose a document to upload, or drag and drop it here"),
           fr=filerow("dz", "drop.dz.removeAria"))

SUCCESS = '<div class="alert ok" role="status">{{successText}}</div>'

FORM = T("""
<sc-if value="{{showProject}}" hint-placeholder-val="{{true}}">[[proj]]</sc-if>
[[drop]]
<sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><div class="alert err" role="alert">{{errorText}}</div></sc-if>
<button class="btn primary {{submitCls}}" style="width:100%;height:40px" onClick="{{submit}}">{{submitLabel}}</button>
""", proj=PROJECT_FIELD, drop=DROPZONE)

BODY = T("""
<div class="row" style="gap:6px;margin-bottom:14px;font-size:13px;color:var(--ink2)">[[back]]<a href="#" style="color:inherit">Back to SOW Review</a></div>
<div class="card" style="max-width:520px;margin:0 auto">
  <div class="card-h"><h2 style="font-size:16px">{{title}}</h2></div>
  <div class="card-b stack" style="gap:14px">
    <p class="sub" style="font-size:13px">{{description}}</p>
    <sc-if value="{{done}}" hint-placeholder-val="{{false}}">[[success]]</sc-if>
    <sc-if value="{{notDone}}" hint-placeholder-val="{{true}}">[[form]]</sc-if>
  </div>
</div>""", back=icon("arrow-left", 14), success=SUCCESS, form=FORM)

VALS = r"""
const mode = P.mode || 'new';
const PRESET = 'NovaRetail Software Solutions';
const drop = { dz: Object.assign(self.dropVals('dz', 'SOC_SOW_Testing_v7.docx', '(2.4 MB)'), { removeAria: 'Remove SOC_SOW_Testing_v7.docx' }) };
const projMode = S.projMode || 'preset';
const projValue = S.projectValue != null ? S.projectValue : PRESET;
const hasProject = mode === 'version' || projMode === 'preset' || !!projValue.trim();
const hasFile = drop.dz.has;
const done = !!S.done;
const errorText = !hasFile ? 'Please select a file' : (mode === 'new' && !hasProject ? 'Choose an existing project or type a new project name' : 'Upload failed');
// other verbatim guard copy kept for completeness (not wired to real checks -- this mock never fails
// file-type/size/org detection): "Only PDF, DOCX, DOC, XLSX, XLS, and CSV files are supported",
// "File size must be less than 50MB", "Unable to determine your organization -- try refreshing the page",
// "Failed to load user info"
return {
  drop,
  title: mode === 'version' ? 'Upload New Version' : 'Upload Document',
  description: mode === 'version' ? 'This file will be linked as the next version of the source document.' : 'Upload a SOW, Proposal, or other document for review',
  showProject: mode !== 'version',
  proj: {
    preset: projMode === 'preset', free: projMode === 'free', name: PRESET || 'Selected project', value: projValue,
    change: () => self.setState({ projMode: 'free', projectValue: PRESET }),
    setValue: e => self.setIn(['projectValue'], e.target.value),
  },
  projects: D.projects,
  errorText,
  done, notDone: !done,
  successText: mode === 'version' ? 'Uploaded as version 7' : ('Document uploaded successfully: ' + drop.dz.file),
  submitCls: (!hasFile || !hasProject || self.busy('upload')) ? 'disabled' : '',
  submitLabel: self.busy('upload') ? 'Uploading...' : 'Upload Document',
  submit: () => { if (!hasFile || !hasProject) return; self.runBusy('upload', 700, () => self.setIn(['done'], true)); },
};
"""

CLICKS = [
    {"text": "Change", "check": "document.querySelector('input[list=\"upload-projects\"]') !== null"},
    {"css": "div[aria-label='Choose a document to upload, or drag and drop it here']", "check": "document.querySelector('.filerow') !== null"},
    {"css": "button.btn.primary", "check": "document.querySelector('[role=\"status\"]') !== null"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    props = {
        "view": {"editor": "enum", "options": ["default", "error"], "default": "default", "section": "State"},
        "mode": {"editor": "enum", "options": ["new", "version"], "default": "new", "section": "State"},
    }
    html = screen(stem, app_shell("dashboard", BODY), VALS, DATA, {"projMode": "preset", "done": False}, props=props, phone=phone)
    return [(stem, html)]
