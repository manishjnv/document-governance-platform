  // ---- shared helpers (class methods so nothing lives at script top level) ----
  setIn(path, val){ const s = JSON.parse(JSON.stringify(this.state)); let o = s;
    for (let i = 0; i < path.length - 1; i++) { if (o[path[i]] == null) o[path[i]] = {}; o = o[path[i]]; }
    o[path[path.length - 1]] = val; this.setState(s); }
  vw(){ return (typeof window !== 'undefined' && window.innerWidth) ? window.innerWidth : 1440; }
  viewFlags(){ const v = (this.props && this.props.view) || 'default';
    return { default: v === 'default', loading: v === 'loading', empty: v === 'empty', error: v === 'error', gated: v === 'gated' }; }
  closeAll(){ if (this.state.menu !== null || this.state.listbox !== null) this.setState({ menu: null, listbox: null }); }
  shellVals(){ const s = this.state.shell; const c = s.collapsed; const w = c ? 56 : s.width;
    return { sideW: w + 'px', cls: c ? 'c' : '', collapsed: c, expanded: !c, togLabel: c ? 'Expand sidebar' : 'Collapse sidebar',
      admin: !(this.props && this.props.admin === false),
      toggle: (e) => { e && e.stopPropagation && e.stopPropagation(); this.setIn(['shell', 'collapsed'], !c); },
      gDown: (e) => { e.currentTarget.setPointerCapture(e.pointerId); this._drag = { kind: 'side', x0: e.clientX, w0: s.width }; },
      gMove: (e) => { if (!this._drag || this._drag.kind !== 'side') return; const nw = Math.max(180, Math.min(400, this._drag.w0 + (e.clientX - this._drag.x0))); this.setIn(['shell', 'width'], nw); },
      gUp: () => { this._drag = null; },
      mTx: s.mobileOpen ? 'translateX(0)' : 'translateX(-105%)', mOvOp: s.mobileOpen ? 1 : 0, mPe: s.mobileOpen ? 'auto' : 'none',
      openMobile: () => this.setIn(['shell', 'mobileOpen'], true), closeMobile: () => this.setIn(['shell', 'mobileOpen'], false) }; }
  tabVals(key, keys){ const cur = this.state.tab[key] || keys[0]; const o = {};
    keys.forEach(k => { const on = cur === k; o[k] = { on: on, cls: on ? 'on' : '', aria: on ? 'true' : 'false', pick: () => this.setIn(['tab', key], k) }; });
    o.current = cur; return o; }
  sheetVals(name, def){ const s = this.state.sheets[name] || { open: false, id: null, width: def || 448 };
    const w = Math.min(s.width, this.vw() * 0.95); const order = this.state.sheetOrder.indexOf(name); const z = 41 + (order < 0 ? 0 : order * 2);
    return { open: s.open, id: s.id, w: w + 'px', tx: s.open ? 'translateX(0)' : 'translateX(105%)', ovOp: s.open ? 1 : 0, pe: s.open ? 'auto' : 'none', z: z, oz: z - 1,
      close: (e) => { e && e.stopPropagation && e.stopPropagation(); this.closeSheet(name); },
      gDown: (e) => { e.currentTarget.setPointerCapture(e.pointerId); this._drag = { kind: name, x0: e.clientX, w0: s.width }; },
      gMove: (e) => { if (!this._drag || this._drag.kind !== name) return; const nw = Math.max(360, Math.min(this.vw() * 0.95, this._drag.w0 - (e.clientX - this._drag.x0))); this.setIn(['sheets', name, 'width'], nw); },
      gUp: () => { this._drag = null; },
      gKey: (e) => { if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); const d = e.key === 'ArrowLeft' ? 40 : -40;
        this.setIn(['sheets', name, 'width'], Math.max(360, Math.min(this.vw() * 0.95, s.width + d))); } } }; }
  openSheet(name, id, def){ const sheets = Object.assign({}, this.state.sheets);
    sheets[name] = Object.assign({ width: def || 448 }, sheets[name] || {}, { open: true, id: id == null ? null : id });
    this.setState({ sheets: sheets, sheetOrder: this.state.sheetOrder.filter(n => n !== name).concat([name]), menu: null, listbox: null }); }
  closeSheet(name){ const sheets = Object.assign({}, this.state.sheets); if (sheets[name]) sheets[name] = Object.assign({}, sheets[name], { open: false });
    this.setState({ sheets: sheets, sheetOrder: this.state.sheetOrder.filter(n => n !== name) }); }
  dlgVals(name){ const on = this.state.dlg === name;
    return { open: on, op: on ? 1 : 0, pe: on ? 'auto' : 'none', tx: on ? 'scale(1)' : 'scale(.96)',
      close: (e) => { e && e.stopPropagation && e.stopPropagation(); this.setState({ dlg: null, dlgArg: null }); },
      key: (e) => { if (e.key === 'Escape') this.setState({ dlg: null, dlgArg: null }); } }; }
  openDlg(name, arg){ this.setState({ dlg: name, dlgArg: arg == null ? null : arg, menu: null, listbox: null }); }
  menuVals(id){ const on = this.state.menu === id;
    return { cls: on ? 'open' : '', toggle: (e) => { e.stopPropagation(); this.setState({ menu: on ? null : id, listbox: null }); } }; }
  lbVals(name){ const on = this.state.listbox === name;
    return { open: on, cls: on ? 'open' : '', aria: on ? 'true' : 'false', toggle: (e) => { e.stopPropagation(); this.setState({ listbox: on ? null : name, menu: null }); } }; }
  sortVals(name, rows, cols, defKey, defDir){ const st = this.state.sort[name] || { key: defKey, dir: defDir || 'asc' }; const col = cols.find(c => c.key === st.key);
    const get = (r) => col && col.get ? col.get(r) : r[st.key];
    const sorted = rows.slice().sort((a, b) => { const va = get(a), vb = get(b); if (va == null && vb == null) return 0; if (va == null) return 1; if (vb == null) return -1;
      const r = (typeof va === 'number' && typeof vb === 'number') ? va - vb : String(va).localeCompare(String(vb)); return st.dir === 'asc' ? r : -r; });
    const h = {}; cols.forEach(c => { const on = c.key === st.key; h[c.key] = { aria: on ? (st.dir === 'asc' ? 'ascending' : 'descending') : 'none', arrow: on ? (st.dir === 'asc' ? '↑' : '↓') : '↕', op: on ? 1 : .35,
      pick: () => this.setIn(['sort', name], { key: c.key, dir: on && st.dir === 'asc' ? 'desc' : 'asc' }) }; });
    return { rows: sorted, h: h, key: st.key, dir: st.dir }; }
  dropVals(name, sample, size){ const d = this.state.drop[name] || { active: false, file: null };
    return { cls: d.active ? 'on' : '', file: d.file || '', size: d.file ? (size || '') : '', has: !!d.file, none: !d.file,
      over: (e) => { e.preventDefault(); if (!d.active) this.setIn(['drop', name, 'active'], true); },
      leave: () => { if (d.active) this.setIn(['drop', name, 'active'], false); },
      pick: (e) => { e && e.preventDefault && e.preventDefault(); this.setIn(['drop', name], { active: false, file: sample }); },
      clear: (e) => { e && e.stopPropagation && e.stopPropagation(); this.setIn(['drop', name], { active: false, file: null }); } }; }
  reqVals(){ const r = this.state.req;
    return { sent: r.sent, form: !r.sent, name: r.name, email: r.email, btn: r.busy ? 'Sending...' : 'Request access',
      setName: (e) => this.setIn(['req', 'name'], e.target.value), setEmail: (e) => this.setIn(['req', 'email'], e.target.value),
      submit: () => { this.setIn(['req', 'busy'], true); setTimeout(() => this.setState({ req: Object.assign({}, this.state.req, { busy: false, sent: true }) }), 700); } }; }
  busy(key){ return !!this.state.busy[key]; }
  runBusy(key, ms, after){ const b = Object.assign({}, this.state.busy); b[key] = true; this.setState({ busy: b });
    setTimeout(() => { const b2 = Object.assign({}, this.state.busy); delete b2[key]; this.setState({ busy: b2 }); if (after) after(); }, ms || 900); }
  isOpen(id){ return !!this.state.expanded[id]; }
  toggleOpen(id){ this.setIn(['expanded', id], !this.state.expanded[id]); }
  renameVals(id, current, onCommit){ const r = this.state.rename; const on = r.id === id;
    return { on: on, off: !on, value: on ? r.value : current,
      start: (e) => { e && e.stopPropagation && e.stopPropagation(); this.setState({ rename: { id: id, value: current }, menu: null }); },
      set: (e) => this.setIn(['rename', 'value'], e.target.value),
      commit: (e) => { e && e.stopPropagation && e.stopPropagation(); const v = (this.state.rename.value || '').trim(); if (!v) return; if (onCommit) onCommit(v); this.setIn(['rename'], { id: null, value: '' }); },
      cancel: (e) => { e && e.stopPropagation && e.stopPropagation(); this.setIn(['rename'], { id: null, value: '' }); },
      key: (e) => { if (e.key === 'Enter') { const v = (this.state.rename.value || '').trim(); if (!v) return; if (onCommit) onCommit(v); this.setIn(['rename'], { id: null, value: '' }); }
        if (e.key === 'Escape') this.setIn(['rename'], { id: null, value: '' }); },
      canSave: !on || !!(r.value || '').trim() }; }
