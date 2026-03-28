# 📡 Notification API — Flask + SQLite (Self-Contained)

A notification API where **all data is stored inside the server itself** using SQLite.
No external database, no cloud storage — everything lives in one place.

When you publish a new notification, the old one is **automatically deleted**.
Deleted messages are saved to a history log (last 10 kept).

---

## 📁 Project Structure

```
notif-api/
├── api/
│   └── index.py       ← Flask app + SQLite logic (Vercel entry point)
├── vercel.json        ← Vercel routing config
├── requirements.txt   ← Python dependencies (flask only)
└── README.md
```

---

## 🚀 Deploy to Vercel via GitHub

### Step 1 — Create GitHub Repository
1. Go to https://github.com → **New repository**
2. Name it: `notification-api`  
3. Set to **Public**
4. Click **Create repository**

### Step 2 — Upload Files
Upload maintaining the folder structure:
```
api/index.py
vercel.json
requirements.txt
README.md
```
Either drag-and-drop in GitHub UI, or use Git:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/notification-api.git
git push -u origin main
```

### Step 3 — Deploy on Vercel
1. Go to https://vercel.com → sign in with GitHub
2. Click **Add New → Project**
3. Select your `notification-api` repo
4. Click **Deploy** (no extra settings needed)
5. Live in ~30 seconds ✓

Your URL: `https://notification-api-xyz.vercel.app`

---

## 🗄️ How Storage Works

| Platform | Database location | Persists? |
|----------|------------------|-----------|
| Local / Railway / Render | Set `DB_PATH=./data/notif.db` env var | ✅ Yes |
| Vercel (serverless) | `/tmp/notifications.db` | ⚠️ Per cold-start |

**For permanent persistence on Vercel:** Set the environment variable `DB_PATH` to a
mounted volume path, or use Railway/Render where `/tmp` is persistent.

**Railway (recommended for permanent storage):**
1. https://railway.app → New Project → Deploy from GitHub
2. Set env var: `DB_PATH=/app/data/notif.db`
3. Done — data survives restarts.

---

## 📡 API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/` | Admin panel (browser) |
| `GET` | `/message` | Current notification JSON → for your app |
| `POST` | `/admin/update` | Publish new notification (deletes old) |
| `GET` | `/history` | Last 10 deleted notifications |

### GET /message — Response
```json
{
  "status": "ok",
  "notification": {
    "title": "New Update!",
    "message": "Version 2.0 is here.",
    "link": "https://t.me/jieshuohelperinternational",
    "link_name": "Join Telegram",
    "updated_at": "2025-03-28 10:00 UTC"
  }
}
```

### POST /admin/update — Body
```json
{
  "title": "Hello Users!",
  "message": "Check out our new feature.",
  "link": "https://example.com",
  "link_name": "Open"
}
```

---

## 💻 Run Locally

```bash
pip install flask
python api/index.py
```
Open: http://localhost:5000/

To set a custom DB path locally:
```bash
DB_PATH=./notifications.db python api/index.py
```

---

## 📱 Use in Your App (AndroLua example)

```lua
local http = require("socket.http")
local json = require("json")

local body = http.request("https://your-app.vercel.app/message")
local data = json.decode(body)
local n = data.notification

-- n.title, n.message, n.link, n.link_name
```
