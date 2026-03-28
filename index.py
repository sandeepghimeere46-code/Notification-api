"""
Notification API — Flask + SQLite
- Self-contained: SQLite database stored inside the server, no external services
- Auto-delete: every new notification wipes the old one (only 1 ever stored)
- Endpoints:
    GET  /           → Admin panel (browser)
    GET  /message    → Current notification JSON (for your app)
    POST /admin/update → Publish new notification (deletes old)
    GET  /history    → Last 10 notifications log (admin only)
"""

from flask import Flask, jsonify, request, Response
import sqlite3, os, datetime

app = Flask(__name__)

# ── Database path ─────────────────────────────────────────────────
# /tmp is writable on Vercel (per-instance).
# For Railway / Render / local: use a persistent path like ./data/notif.db
DB_PATH = os.environ.get("DB_PATH", "/tmp/notifications.db")

# ── DB bootstrap ──────────────────────────────────────────────────
def get_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                message    TEXT    NOT NULL,
                link       TEXT    DEFAULT '',
                link_name  TEXT    DEFAULT 'Learn More',
                created_at TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT,
                message    TEXT,
                link       TEXT,
                link_name  TEXT,
                created_at TEXT
            )
        """)
        conn.commit()

init_db()


# ── Helpers ───────────────────────────────────────────────────────
def current_notification():
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM notifications ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row:
        return dict(row)
    return {
        "title":      "Welcome!",
        "message":    "No notification yet. Open the admin panel to send one.",
        "link":       "",
        "link_name":  "Learn More",
        "created_at": ""
    }

def publish_notification(title, message, link, link_name):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    with get_db() as conn:
        # Archive current to history before deleting
        old = conn.execute("SELECT * FROM notifications").fetchall()
        for row in old:
            conn.execute(
                "INSERT INTO history (title,message,link,link_name,created_at) VALUES (?,?,?,?,?)",
                (row["title"], row["message"], row["link"], row["link_name"], row["created_at"])
            )
        # ── Delete ALL old notifications ──────────────────────────
        conn.execute("DELETE FROM notifications")
        # ── Insert new one ────────────────────────────────────────
        conn.execute(
            "INSERT INTO notifications (title,message,link,link_name,created_at) VALUES (?,?,?,?,?)",
            (title, message, link, link_name, now)
        )
        conn.commit()
    return now


# ── GET /message ──────────────────────────────────────────────────
@app.route("/message")
def get_message():
    n = current_notification()
    return jsonify({
        "status": "ok",
        "notification": {
            "title":      n["title"],
            "message":    n["message"],
            "link":       n["link"],
            "link_name":  n["link_name"],
            "updated_at": n["created_at"]
        }
    })


# ── POST /admin/update ────────────────────────────────────────────
@app.route("/admin/update", methods=["POST"])
def admin_update():
    body = request.get_json(silent=True) or {}
    title    = (body.get("title")    or "").strip()
    message  = (body.get("message")  or "").strip()
    link     = (body.get("link")     or "").strip()
    link_name= (body.get("link_name")or "Learn More").strip()

    if not title or not message:
        return jsonify({"status": "error", "error": "title and message are required"}), 400

    ts = publish_notification(title, message, link, link_name)
    return jsonify({
        "status":  "ok",
        "message": "Notification published. Old message deleted.",
        "published_at": ts
    })


# ── GET /history ──────────────────────────────────────────────────
@app.route("/history")
def history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT 10"
        ).fetchall()
    return jsonify({
        "status":  "ok",
        "history": [dict(r) for r in rows]
    })


# ── GET / — Admin panel ───────────────────────────────────────────
ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Notification Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
:root{
  --bg:#0a0a0f;--surface:#12121a;--card:#1a1a28;--border:#2a2a40;
  --accent:#7c6af7;--accent2:#f76a8a;--green:#4ade80;
  --text:#e8e8f0;--muted:#7070a0;--r:14px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'DM Mono',monospace;
  min-height:100vh;display:flex;flex-direction:column;align-items:center}
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background:radial-gradient(ellipse 60% 40% at 20% 10%,#7c6af715 0%,transparent 60%),
             radial-gradient(ellipse 40% 50% at 80% 80%,#f76a8a10 0%,transparent 60%)}

.wrap{position:relative;z-index:1;width:100%;max-width:700px;padding:48px 24px 90px}

/* header */
header{margin-bottom:40px}
.badge{display:inline-block;background:linear-gradient(135deg,#7c6af720,#f76a8a20);
  border:1px solid var(--border);color:var(--accent);font-size:11px;letter-spacing:3px;
  text-transform:uppercase;padding:5px 14px;border-radius:99px;margin-bottom:18px}
h1{font-family:'Syne',sans-serif;font-size:clamp(26px,5vw,40px);font-weight:800;
  line-height:1.1;background:linear-gradient(135deg,#fff 30%,#7c6af7 80%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;margin-bottom:10px}
.sub{color:var(--muted);font-size:13px}

/* card */
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:30px;margin-bottom:22px;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--accent),transparent);opacity:.5}
.ct{font-family:'Syne',sans-serif;font-weight:700;font-size:12px;letter-spacing:2px;
  text-transform:uppercase;color:var(--accent);margin-bottom:22px;
  display:flex;align-items:center;gap:8px}
.ct span{font-size:15px}

/* form */
.field{margin-bottom:18px}
label{display:block;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--muted);margin-bottom:7px}
input,textarea{width:100%;background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:12px 15px;color:var(--text);font-family:'DM Mono',monospace;
  font-size:14px;outline:none;transition:border-color .2s,box-shadow .2s;resize:vertical}
input:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px #7c6af720}
textarea{min-height:100px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:480px){.row{grid-template-columns:1fr}}

/* button */
.btn{display:inline-flex;align-items:center;gap:8px;justify-content:center;
  background:linear-gradient(135deg,var(--accent),#9b5de5);color:#fff;border:none;
  border-radius:10px;padding:13px 26px;font-family:'Syne',sans-serif;font-weight:700;
  font-size:14px;letter-spacing:1px;cursor:pointer;transition:opacity .2s,transform .15s;width:100%}
.btn:hover{opacity:.87;transform:translateY(-1px)}
.btn:active{transform:translateY(0)}

/* preview / current */
.pbox{background:linear-gradient(135deg,#1e1e30,#14141f);border:1px solid var(--border);
  border-radius:11px;padding:18px;margin-top:10px}
.ptitle{font-family:'Syne',sans-serif;font-weight:700;font-size:15px;color:#fff;
  margin-bottom:7px;word-break:break-word}
.pmsg{color:var(--muted);font-size:13px;line-height:1.6;margin-bottom:12px;word-break:break-word}
.plink{display:inline-flex;align-items:center;gap:6px;background:var(--accent);color:#fff;
  padding:7px 16px;border-radius:8px;font-family:'Syne',sans-serif;font-size:12px;
  font-weight:700;text-decoration:none;transition:opacity .2s}
.plink:hover{opacity:.8}
.nolink{color:var(--muted);font-size:12px;font-style:italic}

/* status tag */
.tag{font-size:11px;padding:4px 10px;border-radius:99px;letter-spacing:1px}
.gtag{color:var(--green);background:#4ade8015;border:1px solid #4ade8030}
.rtag{color:var(--accent2);background:#f76a8a10;border:1px solid #f76a8a30}

/* api ref */
.ep{background:var(--surface);border:1px solid var(--border);border-radius:9px;
  padding:12px 16px;font-size:12px;margin-bottom:10px;display:flex;align-items:center;
  gap:10px;flex-wrap:wrap}
.m{font-family:'Syne',sans-serif;font-weight:700;font-size:10px;letter-spacing:1px;
  padding:3px 8px;border-radius:5px}
.mg{background:#4ade8020;color:var(--green);border:1px solid #4ade8040}
.mp{background:#7c6af720;color:var(--accent);border:1px solid #7c6af740}
.eu{color:var(--muted);flex:1;word-break:break-all}
.ed{font-size:11px;color:#50508a;width:100%;margin-top:3px}

/* history */
.hrow{background:var(--surface);border:1px solid var(--border);border-radius:9px;
  padding:12px 16px;margin-bottom:8px}
.htitle{font-family:'Syne',sans-serif;font-weight:700;font-size:13px;color:#fff;margin-bottom:3px}
.hmsg{color:var(--muted);font-size:12px;margin-bottom:5px}
.hmeta{font-size:11px;color:#50508a;display:flex;gap:10px;flex-wrap:wrap}
.deleted-badge{display:inline-block;background:#f76a8a10;border:1px solid #f76a8a30;
  color:var(--accent2);font-size:10px;padding:2px 8px;border-radius:99px;margin-left:6px}

/* divider */
.div{height:1px;background:var(--border);margin:6px 0 18px}

/* toast */
#toast{position:fixed;bottom:28px;left:50%;transform:translateX(-50%) translateY(16px);
  background:var(--card);border:1px solid var(--border);color:var(--text);
  padding:11px 22px;border-radius:9px;font-size:13px;opacity:0;transition:all .3s;
  z-index:999;white-space:nowrap;pointer-events:none}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
#toast.ok{border-color:var(--green);color:var(--green)}
#toast.err{border-color:var(--accent2);color:var(--accent2)}

/* db info */
.dbinfo{background:var(--surface);border:1px solid var(--border);border-radius:9px;
  padding:12px 16px;font-size:12px;color:var(--muted);display:flex;align-items:center;gap:8px}
.dbdot{width:8px;height:8px;border-radius:50%;background:var(--green);
  box-shadow:0 0 6px var(--green);flex-shrink:0}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="badge">Admin Panel</div>
  <h1>Notification<br>Control Center</h1>
  <p class="sub">Built-in SQLite storage · Old messages auto-deleted on publish</p>
</header>

<!-- DB STATUS -->
<div class="card">
  <div class="ct"><span>◈</span> Server Storage</div>
  <div class="dbinfo">
    <div class="dbdot"></div>
    <span>SQLite database running on this server — no external service needed. 
    Data stored at <code>/tmp/notifications.db</code> (or custom <code>DB_PATH</code> env var).</span>
  </div>
</div>

<!-- COMPOSE -->
<div class="card">
  <div class="ct"><span>✦</span> Publish New Notification</div>
  <p style="font-size:12px;color:var(--muted);margin-bottom:20px">
    ⚠ Publishing replaces the current notification immediately. The old one is moved to history.
  </p>

  <div class="field">
    <label>Title *</label>
    <input id="f-title" type="text" placeholder="e.g. New Update Available!" maxlength="120"/>
  </div>
  <div class="field">
    <label>Message *</label>
    <textarea id="f-message" placeholder="Write your notification message here..."></textarea>
  </div>
  <div class="row">
    <div class="field">
      <label>Button Link URL</label>
      <input id="f-link" type="url" placeholder="https://example.com"/>
    </div>
    <div class="field">
      <label>Button Label</label>
      <input id="f-linkname" type="text" placeholder="Learn More" maxlength="40"/>
    </div>
  </div>

  <button class="btn" onclick="publish()">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 2L11 13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
    Publish &amp; Replace Old Notification
  </button>
</div>

<!-- PREVIEW -->
<div class="card">
  <div class="ct"><span>◎</span> Live Preview</div>
  <div class="pbox">
    <div class="ptitle" id="pv-t">Your title here</div>
    <div class="pmsg"  id="pv-m">Your message will appear here...</div>
    <span id="pv-lw"></span>
  </div>
</div>

<!-- CURRENT -->
<div class="card">
  <div class="ct"><span>◉</span> Current Live Notification</div>
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px">
    <span id="c-tag" class="tag gtag">Loading...</span>
    <span id="c-time" style="font-size:11px;color:var(--muted)"></span>
  </div>
  <div class="div"></div>
  <div class="pbox" style="margin-top:0">
    <div class="ptitle" id="c-t">—</div>
    <div class="pmsg"  id="c-m">—</div>
    <span id="c-lw"></span>
  </div>
</div>

<!-- HISTORY -->
<div class="card">
  <div class="ct"><span>↺</span> Recent History <span style="font-size:11px;color:var(--muted);text-transform:none;letter-spacing:0">(last 10 deleted messages)</span></div>
  <div id="hist-list"><span style="color:var(--muted);font-size:13px">Loading...</span></div>
</div>

<!-- API REFERENCE -->
<div class="card">
  <div class="ct"><span>⌁</span> API Endpoints</div>
  <div class="ep"><span class="m mg">GET</span><span class="eu">/message</span><span class="ed">Returns current notification JSON for your application.</span></div>
  <div class="ep"><span class="m mp">POST</span><span class="eu">/admin/update</span><span class="ed">Publish new notification — auto-deletes old. Body: {title, message, link, link_name}</span></div>
  <div class="ep"><span class="m mg">GET</span><span class="eu">/history</span><span class="ed">Returns last 10 deleted (archived) notifications as JSON.</span></div>
  <div class="ep"><span class="m mg">GET</span><span class="eu">/</span><span class="ed">This admin panel — open in any browser.</span></div>
</div>

</div><!-- wrap -->
<div id="toast"></div>

<script>
// ── live preview ──────────────────────────────────────────────────
function preview(){
  const t=v('f-title')||'Your title here';
  const m=v('f-message')||'Your message will appear here...';
  const l=v('f-link'), ln=v('f-linkname')||'Learn More';
  document.getElementById('pv-t').textContent=t;
  document.getElementById('pv-m').textContent=m;
  renderLink('pv-lw',l,ln);
}
function v(id){return document.getElementById(id).value.trim()}
['f-title','f-message','f-link','f-linkname'].forEach(id=>
  document.getElementById(id).addEventListener('input',preview));
preview();

// ── publish ───────────────────────────────────────────────────────
async function publish(){
  const title=v('f-title'),message=v('f-message');
  const link=v('f-link'),link_name=v('f-linkname');
  if(!title||!message){toast('Title and message are required!','err');return}
  try{
    const r=await fetch('/admin/update',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title,message,link,link_name})});
    const d=await r.json();
    if(d.status==='ok'){toast('✓ Published! Old notification deleted.','ok');load();loadHist()}
    else toast(d.error||'Error','err');
  }catch{toast('Network error','err')}
}

// ── render link button ────────────────────────────────────────────
function renderLink(wrapId,l,ln){
  const w=document.getElementById(wrapId);
  if(l)w.innerHTML=`<a class="plink" href="${l}" target="_blank">
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>${ln||'Open'}</a>`;
  else w.innerHTML='<span class="nolink">No link</span>';
}

// ── load current ──────────────────────────────────────────────────
async function load(){
  try{
    const d=(await(await fetch('/message')).json()).notification;
    document.getElementById('c-t').textContent=d.title;
    document.getElementById('c-m').textContent=d.message;
    document.getElementById('c-time').textContent=d.updated_at?'Published: '+d.updated_at:'';
    document.getElementById('c-tag').textContent=d.updated_at?'● Live':'Not set';
    renderLink('c-lw',d.link,d.link_name);
  }catch{}
}

// ── load history ──────────────────────────────────────────────────
async function loadHist(){
  try{
    const data=(await(await fetch('/history')).json());
    const el=document.getElementById('hist-list');
    if(!data.history||data.history.length===0){
      el.innerHTML='<span style="color:var(--muted);font-size:13px">No history yet — previous notifications appear here when replaced.</span>';
      return;
    }
    el.innerHTML=data.history.map(h=>`
      <div class="hrow">
        <div class="htitle">${h.title}<span class="deleted-badge">deleted</span></div>
        <div class="hmsg">${h.message}</div>
        <div class="hmeta">
          <span>${h.created_at||'—'}</span>
          ${h.link?`<a href="${h.link}" target="_blank" style="color:var(--accent)">${h.link_name||h.link}</a>`:''}
        </div>
      </div>`).join('');
  }catch{}
}

// ── toast ─────────────────────────────────────────────────────────
let tt;
function toast(msg,type=''){
  const el=document.getElementById('toast');
  el.textContent=msg;el.className='show '+type;
  clearTimeout(tt);tt=setTimeout(()=>el.className='',3200);
}

load();loadHist();
</script>
</body>
</html>
"""

@app.route("/")
def admin_page():
    return Response(ADMIN_HTML, mimetype="text/html")


if __name__ == "__main__":
    print("\n  Admin : http://localhost:5000/")
    print("  API   : http://localhost:5000/message")
    print("  Hist  : http://localhost:5000/history\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
