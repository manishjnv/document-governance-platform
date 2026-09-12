"""/login — sign-in screen, no AppShell. Source: inventory/codereview_admin_login.md §C."""
from dc import T, screen, icon

STEM = "Login"
PAGE, TITLE, ORDER = "admin", "Login", 90

DATA = {}

GOOGLE_G = """<svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
<path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84c-.21 1.12-.84 2.07-1.8 2.71v2.26h2.92c1.7-1.57 2.68-3.87 2.68-6.61z"/>
<path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.71H.96v2.33C2.44 15.98 5.48 18 9 18z"/>
<path fill="#FBBC05" d="M3.97 10.71A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.71V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3.01-2.33z"/>
<path fill="#EA4335" d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.59-2.59C13.46.89 11.43 0 9 0 5.48 0 2.44 2.02.96 4.96l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
</svg>"""

SR_ONLY = "position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0"

GOOGLE_BTN = T("""<button class="btn" style="width:100%;max-width:336px;height:44px;margin:0 auto;display:flex;align-items:center;justify-content:center" aria-label="Sign in with Google">[[g]]<span style="font-weight:500;margin-left:8px">Sign in with Google</span></button>""", g=GOOGLE_G)

GOOGLE_LOADING = '<div class="skel" style="height:44px;max-width:336px;margin:0 auto;border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--ink3);font-size:13px">Loading Google sign-in…</div>'

EMAIL_STEP = T("""<div>
<label style="[[sr]]" for="login-email">Your email address</label>
<input id="login-email" class="input" style="width:100%" type="email" placeholder="you@example.com" value="{{email}}" onChange="{{setEmail}}">
<button class="btn primary" style="width:100%;height:40px;margin-top:10px" onClick="{{sendCode}}">{{sendLabel}}</button>
<p class="faint" style="font-size:12px;margin-top:8px">We'll email you a 4-digit code — no password needed.</p>
</div>""", sr=SR_ONLY)

CODE_STEP = T("""<div>
<p style="font-size:13.5px">Enter the 4-digit code sent to <b>{{email}}</b>.</p>
<div class="row" style="gap:8px;margin-top:10px">
  <input class="input mono" aria-label="Sign-in code" style="flex:1;text-align:center;letter-spacing:.35em;font-size:18px" type="{{codeType}}" inputmode="numeric" maxlength="4" value="{{code}}" onChange="{{setCode}}">
  <button class="xbtn tip" data-tip="{{eyeLabel}}" aria-label="{{eyeLabel}}" onClick="{{toggleEye}}" style="border:1px solid var(--line2);border-radius:8px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;flex:none">
    <sc-if value="{{codeHidden}}" hint-placeholder-val="{{true}}">[[eye]]</sc-if>
    <sc-if value="{{codeVisible}}" hint-placeholder-val="{{false}}">[[eyeOff]]</sc-if>
  </button>
</div>
<sc-if value="{{verifying}}" hint-placeholder-val="{{false}}"><p class="faint" style="font-size:12px;margin-top:6px">Verifying...</p></sc-if>
<button class="btn link" style="margin-top:12px;font-size:13px;padding:0;height:auto" onClick="{{useOther}}">Use a different email</button>
</div>""", eye=icon("eye", 16), eyeOff=icon("eye-off", 16))

BODY = T("""
<div data-screen="[[stem]]" data-ready="{{ready}}" onClick="{{root}}" style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--paper);padding:24px">
  <div class="card rise" style="width:100%;max-width:392px;padding:28px 26px 24px">
    <div style="text-align:center;margin-bottom:18px">
      <div style="display:flex;justify-content:center;color:var(--accent);margin-bottom:10px">[[shield]]</div>
      <h1 style="font-size:19px">ScopeWise</h1>
      <p class="sub" style="font-size:13px;margin-top:4px">Catch contract risk before you sign.</p>
    </div>
    <sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><div class="alert err" role="alert" style="margin-bottom:14px">{{errorText}}</div></sc-if>
    <sc-if value="{{showGoogle}}" hint-placeholder-val="{{true}}">[[gbtn]]</sc-if>
    <sc-if value="{{is.loading}}" hint-placeholder-val="{{false}}">[[gload]]</sc-if>
    <div class="row" style="gap:10px;align-items:center;margin:18px 0">
      <span style="flex:1;height:1px;background:var(--line)"></span>
      <span class="chip outline xs">Or sign in with a code</span>
      <span style="flex:1;height:1px;background:var(--line)"></span>
    </div>
    <sc-if value="{{stepEmail}}" hint-placeholder-val="{{true}}">[[emailStep]]</sc-if>
    <sc-if value="{{stepCode}}" hint-placeholder-val="{{false}}">[[codeStep]]</sc-if>
  </div>
</div>""", shield=icon("shield", 26), gbtn=GOOGLE_BTN, gload=GOOGLE_LOADING, emailStep=EMAIL_STEP, codeStep=CODE_STEP)

VALS = r"""
const step = S.step || 'email';
const email = S.email != null ? S.email : 'jordan@acme.com';
const code = S.code || '';
const codeVisible = !!S.codeVisible;
return {
  errorText: step === 'code' ? "That code didn't match. Please try again." : 'Failed to send code',
  showGoogle: P.view !== 'loading',
  stepEmail: step === 'email', stepCode: step === 'code',
  email, setEmail: e => self.setIn(['email'], e.target.value),
  sendLabel: self.busy('send') ? 'Sending your code...' : 'Email me a sign-in code',
  sendCode: () => self.runBusy('send', 700, () => self.setIn(['step'], 'code')),
  code, setCode: e => { const v = e.target.value.replace(/\D/g, '').slice(0, 4); self.setIn(['code'], v); if (v.length === 4) self.runBusy('verify', 700); },
  verifying: self.busy('verify'),
  codeVisible, codeHidden: !codeVisible, codeType: codeVisible ? 'text' : 'password',
  eyeLabel: codeVisible ? 'Hide code' : 'Show code',
  toggleEye: () => self.setIn(['codeVisible'], !codeVisible),
  useOther: () => self.setState({ step: 'email', code: '', codeVisible: false }),
};
"""

CLICKS = [
    {"text": "Email me a sign-in code", "check": "document.querySelector('input[maxlength=\"4\"]') !== null"},
    {"label": "Show code", "check": "document.querySelector('[aria-label=\"Hide code\"]') !== null"},
    {"text": "Use a different email", "check": "document.querySelector('input[maxlength=\"4\"]') === null"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    props = {"view": {"editor": "enum", "options": ["default", "loading", "error"], "default": "default", "section": "State"}}
    html = screen(stem, BODY, VALS, DATA, {"step": "email", "email": "jordan@acme.com", "code": "", "codeVisible": False}, props=props, phone=phone)
    return [(stem, html)]
