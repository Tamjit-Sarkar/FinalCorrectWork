from fastapi import FastAPI, Form, Request, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional
import os
import secrets

app = FastAPI()

# ─── Auth ────────────────────────────────────────────────────────────────────
APP_PASSWORD = os.environ.get("APP_PASSWORD", "taskflow2024")
sessions: set = set()


def is_authenticated(session: Optional[str]) -> bool:
    return session is not None and session in sessions


# ─── Data ────────────────────────────────────────────────────────────────────
tasks: list = []
next_task_id: int = 1


class Task(BaseModel):
    title: str
    category: str
    priority: str
    due_date: str
    task_type: str


# ─── Landing Page ─────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def landing():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taskflow — Own your time</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --black: #0a0a0a;
    --white: #fafaf9;
    --red: #e63946;
    --red-dark: #c1121f;
    --gray-1: #1c1c1e;
    --gray-2: #2c2c2e;
    --gray-3: #48484a;
    --gray-5: #aeaeb2;
    --gray-6: #d1d1d6;
    --gray-7: #f2f2f7;
  }

  html { scroll-behavior: smooth; }

  body {
    font-family: 'Inter', sans-serif;
    background: var(--black);
    color: var(--white);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* ── NAV ── */
  nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 48px;
    background: rgba(10,10,10,0.8);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  .nav-logo {
    font-size: 17px; font-weight: 700; letter-spacing: -0.3px;
    color: var(--white);
  }
  .nav-logo span { color: var(--red); }
  .nav-cta {
    padding: 9px 22px; border-radius: 8px;
    background: var(--red); color: white;
    font-size: 13px; font-weight: 600; letter-spacing: 0.2px;
    text-decoration: none; transition: background 0.2s;
  }
  .nav-cta:hover { background: var(--red-dark); }

  /* ── HERO ── */
  .hero {
    min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
    text-align: center;
    padding: 120px 24px 80px;
    position: relative;
    overflow: hidden;
  }

  /* Subtle grid background */
  .hero::before {
    content: '';
    position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 40%, transparent 100%);
  }

  /* Red glow blob */
  .hero::after {
    content: '';
    position: absolute;
    width: 600px; height: 400px;
    top: 50%; left: 50%;
    transform: translate(-50%, -60%);
    background: radial-gradient(ellipse, rgba(230,57,70,0.15) 0%, transparent 70%);
    pointer-events: none;
  }

  .hero-content { position: relative; z-index: 1; max-width: 720px; }

  .hero-eyebrow {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 14px; border-radius: 100px;
    border: 1px solid rgba(230,57,70,0.3);
    background: rgba(230,57,70,0.08);
    font-size: 12px; font-weight: 500; color: #ff6b78;
    letter-spacing: 0.6px; text-transform: uppercase;
    margin-bottom: 32px;
  }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--red); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

  .hero h1 {
    font-family: 'Playfair Display', serif;
    font-size: clamp(44px, 7vw, 80px);
    font-weight: 700; line-height: 1.08;
    letter-spacing: -1.5px;
    margin-bottom: 24px;
    color: var(--white);
  }
  .hero h1 em {
    font-style: italic; color: var(--red);
  }

  .hero-sub {
    font-size: 18px; font-weight: 300; line-height: 1.7;
    color: var(--gray-5); max-width: 480px; margin: 0 auto 48px;
  }

  .hero-actions { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }
  .btn-primary {
    padding: 14px 32px; border-radius: 10px;
    background: var(--red); color: white;
    font-size: 15px; font-weight: 600;
    text-decoration: none; transition: all 0.2s;
    box-shadow: 0 0 0 0 rgba(230,57,70,0.4);
  }
  .btn-primary:hover {
    background: var(--red-dark);
    box-shadow: 0 0 0 6px rgba(230,57,70,0.15);
  }
  .btn-ghost {
    padding: 14px 32px; border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.15);
    color: var(--gray-5); font-size: 15px; font-weight: 500;
    text-decoration: none; transition: all 0.2s;
  }
  .btn-ghost:hover { border-color: rgba(255,255,255,0.3); color: var(--white); }

  /* ── FEATURES ── */
  .features {
    padding: 120px 48px;
    max-width: 1100px; margin: 0 auto;
  }
  .section-label {
    font-size: 11px; font-weight: 600; letter-spacing: 2px;
    text-transform: uppercase; color: var(--red);
    margin-bottom: 16px;
  }
  .section-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(32px, 4vw, 48px);
    font-weight: 700; line-height: 1.2;
    letter-spacing: -0.5px; color: var(--white);
    margin-bottom: 64px; max-width: 500px;
  }

  .features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; }
  .feature {
    padding: 36px 32px;
    background: var(--gray-1);
    transition: background 0.2s;
  }
  .feature:first-child { border-radius: 12px 0 0 12px; }
  .feature:last-child { border-radius: 0 12px 12px 0; }
  .feature:hover { background: var(--gray-2); }

  .feature-icon {
    width: 40px; height: 40px; border-radius: 10px;
    background: rgba(230,57,70,0.1);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; margin-bottom: 20px;
  }
  .feature h3 { font-size: 16px; font-weight: 600; margin-bottom: 10px; }
  .feature p { font-size: 14px; line-height: 1.7; color: var(--gray-5); }

  /* ── LOGIN ── */
  .login-section {
    padding: 120px 24px;
    display: flex; align-items: center; justify-content: center;
  }
  .login-card {
    background: var(--gray-1);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px;
    padding: 52px 48px;
    width: 100%; max-width: 420px;
    box-shadow: 0 40px 80px rgba(0,0,0,0.4);
  }
  .login-card h2 {
    font-family: 'Playfair Display', serif;
    font-size: 28px; font-weight: 700;
    margin-bottom: 8px;
  }
  .login-card p {
    font-size: 14px; color: var(--gray-5); margin-bottom: 36px;
  }
  .field { margin-bottom: 16px; }
  .field label {
    display: block; font-size: 12px; font-weight: 600;
    letter-spacing: 0.4px; color: var(--gray-5);
    margin-bottom: 8px; text-transform: uppercase;
  }
  .field input {
    width: 100%; padding: 13px 16px;
    background: var(--gray-2); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px; color: var(--white);
    font-size: 15px; font-family: 'Inter', sans-serif;
    transition: border-color 0.2s;
  }
  .field input:focus { outline: none; border-color: var(--red); }
  .field input::placeholder { color: var(--gray-3); }
  .login-btn {
    width: 100%; padding: 14px;
    background: var(--red); border: none; border-radius: 10px;
    color: white; font-size: 15px; font-weight: 600;
    cursor: pointer; margin-top: 8px; transition: all 0.2s;
  }
  .login-btn:hover { background: var(--red-dark); }
  .error-msg {
    background: rgba(230,57,70,0.12); border: 1px solid rgba(230,57,70,0.3);
    border-radius: 8px; padding: 12px 16px;
    color: #ff6b78; font-size: 13px; margin-bottom: 20px;
  }

  /* ── FOOTER ── */
  footer {
    border-top: 1px solid rgba(255,255,255,0.06);
    padding: 32px 48px;
    display: flex; align-items: center; justify-content: space-between;
    color: var(--gray-3); font-size: 13px;
  }
  .footer-logo { font-weight: 700; color: var(--gray-5); }
  .footer-logo span { color: var(--red); }

  /* ── RESPONSIVE ── */
  @media (max-width: 768px) {
    nav { padding: 16px 20px; }
    .features { padding: 80px 20px; }
    .features-grid { grid-template-columns: 1fr; gap: 2px; }
    .feature:first-child { border-radius: 12px 12px 0 0; }
    .feature:last-child { border-radius: 0 0 12px 12px; }
    .login-card { padding: 36px 24px; }
    footer { flex-direction: column; gap: 8px; text-align: center; }
  }
</style>
</head>
<body>

<nav>
  <div class="nav-logo">TASK<span>FLOW</span></div>
  <a href="#login" class="nav-cta">Sign in</a>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="hero-content">
    <div class="hero-eyebrow"><span class="dot"></span> Your personal task OS</div>
    <h1>Stop managing tasks.<br>Start <em>owning</em> your time.</h1>
    <p class="hero-sub">Track priorities, deadlines, and progress — all in one clean workspace built for people who take their work seriously.</p>
    <div class="hero-actions">
      <a href="#login" class="btn-primary">Open dashboard</a>
      <a href="#features" class="btn-ghost">See what's inside</a>
    </div>
  </div>
</section>

<!-- FEATURES -->
<section class="features" id="features">
  <div class="section-label">Why Taskflow</div>
  <div class="section-title">Everything you need.<br>Nothing you don't.</div>
  <div class="features-grid">
    <div class="feature">
      <div class="feature-icon">🎯</div>
      <h3>Priority system</h3>
      <p>Tag every task as High, Medium, or Low — and always know what demands your attention first.</p>
    </div>
    <div class="feature">
      <div class="feature-icon">⏱️</div>
      <h3>Deadline tracking</h3>
      <p>Color-coded deadlines show you what's overdue, urgent, or safely scheduled — at a glance.</p>
    </div>
    <div class="feature">
      <div class="feature-icon">📊</div>
      <h3>Live progress ring</h3>
      <p>A real-time completion ring gives you the honest picture of where you stand today.</p>
    </div>
  </div>
</section>

<!-- LOGIN -->
<section class="login-section" id="login">
  <div class="login-card">
    <h2>Welcome back</h2>
    <p>Enter your password to access the dashboard.</p>
    <form method="POST" action="/login">
      <div class="field">
        <label>Password</label>
        <input type="password" name="password" placeholder="Enter password" autofocus required />
      </div>
      <button type="submit" class="login-btn">Access dashboard →</button>
    </form>
  </div>
</section>

<footer>
  <div class="footer-logo">TASK<span>FLOW</span></div>
  <div>Built with FastAPI · Deployed on Railway</div>
</footer>

</body>
</html>"""


@app.get("/login-error", response_class=HTMLResponse)
def login_error():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taskflow — Sign in</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;700&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'Inter',sans-serif;background:#0a0a0a;color:#fafaf9;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:#1c1c1e;border:1px solid rgba(255,255,255,0.06);border-radius:20px;padding:52px 48px;width:100%;max-width:420px}
  h2{font-family:'Playfair Display',serif;font-size:28px;font-weight:700;margin-bottom:8px}
  p{font-size:14px;color:#aeaeb2;margin-bottom:28px}
  .error{background:rgba(230,57,70,0.12);border:1px solid rgba(230,57,70,0.3);border-radius:8px;padding:12px 16px;color:#ff6b78;font-size:13px;margin-bottom:20px}
  label{display:block;font-size:12px;font-weight:600;letter-spacing:.4px;color:#aeaeb2;margin-bottom:8px;text-transform:uppercase}
  input{width:100%;padding:13px 16px;background:#2c2c2e;border:1px solid rgba(255,255,255,0.08);border-radius:10px;color:#fafaf9;font-size:15px;font-family:'Inter',sans-serif;outline:none}
  input:focus{border-color:#e63946}
  button{width:100%;padding:14px;background:#e63946;border:none;border-radius:10px;color:white;font-size:15px;font-weight:600;cursor:pointer;margin-top:16px}
  button:hover{background:#c1121f}
  .back{display:block;text-align:center;margin-top:16px;color:#aeaeb2;font-size:13px;text-decoration:none}
  .back:hover{color:#fafaf9}
</style>
</head>
<body>
<div class="card">
  <h2>Incorrect password</h2>
  <p>That password didn't match. Please try again.</p>
  <div class="error">⚠ Invalid password</div>
  <form method="POST" action="/login">
    <label>Password</label>
    <input type="password" name="password" placeholder="Enter password" autofocus required />
    <button type="submit">Try again →</button>
  </form>
  <a href="/" class="back">← Back to home</a>
</div>
</body>
</html>"""


# ─── Auth Routes ──────────────────────────────────────────────────────────────
@app.post("/login")
def login(response: Response, password: str = Form(...)):
    if password == APP_PASSWORD:
        token = secrets.token_hex(32)
        sessions.add(token)
        resp = RedirectResponse("/dashboard", status_code=302)
        resp.set_cookie("session", token, httponly=True, max_age=86400 * 7)
        return resp
    return RedirectResponse("/login-error", status_code=302)


@app.get("/logout")
def logout(response: Response, session: Optional[str] = Cookie(default=None)):
    if session and session in sessions:
        sessions.discard(session)
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("session")
    return resp


# ─── Dashboard ────────────────────────────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(session: Optional[str] = Cookie(default=None)):
    if not is_authenticated(session):
        return RedirectResponse("/", status_code=302)

    total = len(tasks)
    completed = len([t for t in tasks if t["completed"]])
    pending = total - completed
    progress = int((completed / total * 100) if total else 0)

    if progress == 0:
        ring_color = "#6b7280"
    elif progress < 33:
        ring_color = "#dc2626"
    elif progress < 66:
        ring_color = "#f59e0b"
    else:
        ring_color = "#10b981"

    tasks_html = ""
    for t in tasks:
        try:
            due = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
            days_left = (due - date.today()).days
        except:
            days_left = 0

        if t["completed"]:
            status = "Completed"
            status_class = "completed"
        elif days_left < 0:
            n = abs(days_left)
            status = f"Overdue by {n} day" + ("s" if n != 1 else "")
            status_class = "overdue"
        elif days_left == 0:
            status = "Due today"
            status_class = "urgent"
        elif days_left == 1:
            status = "Due tomorrow"
            status_class = "upcoming"
        else:
            status = f"{days_left} days left"
            status_class = "normal"

        priority = t["priority"].lower()
        priority_colors = {"high": "#dc2626", "medium": "#f59e0b", "low": "#10b981"}
        priority_bg = {"high": "#fee2e2", "medium": "#fef3c7", "low": "#ecfdf5"}
        color = priority_colors.get(priority, "#666")
        bg = priority_bg.get(priority, "white")

        title_esc = t["title"].replace('"', '&quot;').replace("'", "&#39;")
        cat_esc = t["category"].replace('"', '&quot;').replace("'", "&#39;")

        tasks_html += f"""<div class="task-item {status_class}" style="background-color:{bg}">
            <a href="/task/complete/{t['id']}" class="checkbox {'checked' if t['completed'] else ''}">
                {'✓' if t['completed'] else ''}
            </a>
            <div class="task-main">
                <h3>{t['title']}</h3>
                <p class="task-meta">{t['category']} · {t['task_type']} · {t['due_date']}</p>
            </div>
            <span class="badge" style="background:{color}22;color:{color};border:1px solid {color}44">{priority.upper()}</span>
            <span class="status-label">{status}</span>
            <div class="actions">
                <button onclick="openEdit({t['id']},'{title_esc}','{cat_esc}','{priority}','{t['due_date']}','{t['task_type']}')" class="edit-btn">Edit</button>
                <a href="/task/delete/{t['id']}" class="delete-btn" onclick="return confirm('Delete this task?')">Delete</a>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taskflow — Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; background:#f5f4f2; color:#1a1a1a; }}

  /* NAV */
  .topbar {{
    position:fixed; top:0; left:0; right:0; z-index:100;
    background:#0a0a0a; padding:0 32px;
    display:flex; align-items:center; justify-content:space-between;
    height:56px; border-bottom:1px solid rgba(255,255,255,0.06);
  }}
  .topbar-logo {{ font-weight:700; font-size:16px; color:#fafaf9; }}
  .topbar-logo span {{ color:#e63946; }}
  .topbar-right {{ display:flex; align-items:center; gap:16px; }}
  .topbar-date {{ font-size:13px; color:#6b7280; }}
  .logout {{
    padding:7px 16px; border-radius:7px;
    border:1px solid rgba(255,255,255,0.12); color:#aeaeb2;
    font-size:12px; font-weight:500; text-decoration:none;
    transition:all 0.2s;
  }}
  .logout:hover {{ border-color:rgba(255,255,255,0.3); color:#fafaf9; }}

  /* LAYOUT */
  .page {{ max-width:1200px; margin:0 auto; padding:80px 32px 60px; display:grid; grid-template-columns:1fr 280px; gap:40px; }}

  /* HEADER */
  .page-header {{ grid-column:1; margin-bottom:8px; }}
  .page-header h1 {{
    font-family:'Playfair Display',serif;
    font-size:36px; font-weight:700; letter-spacing:-0.5px;
    margin-bottom:6px;
  }}
  .page-header p {{ font-size:14px; color:#6b7280; }}

  /* FORM */
  .form-card {{
    grid-column:1; background:white; padding:28px 32px;
    border-radius:14px; margin-bottom:32px;
    box-shadow:0 1px 3px rgba(0,0,0,0.05);
  }}
  .form-card-title {{ font-size:13px; font-weight:600; color:#6b7280; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:20px; }}
  .form-grid {{ display:grid; gap:12px; }}
  .form-row {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
  .form-full {{ grid-column:1/-1; }}
  input[type=text], input[type=date], select {{
    width:100%; padding:10px 14px;
    border:1px solid #e5e7eb; border-radius:8px;
    font-size:14px; font-family:'Inter',sans-serif; color:#1a1a1a;
    background:white; transition:border-color 0.2s;
  }}
  input[type=text]:focus, input[type=date]:focus, select:focus {{
    outline:none; border-color:#1a1a1a;
    box-shadow:0 0 0 3px rgba(26,26,26,0.05);
  }}
  .btn-add {{
    width:100%; padding:11px; background:#0a0a0a; color:white;
    border:none; border-radius:8px; font-weight:600; font-size:14px;
    cursor:pointer; transition:opacity 0.2s;
  }}
  .btn-add:hover {{ opacity:0.85; }}

  /* TASKS */
  .tasks-list {{ grid-column:1; display:flex; flex-direction:column; gap:10px; }}
  .tasks-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; }}
  .tasks-header h2 {{ font-size:15px; font-weight:600; }}
  .tasks-count {{ font-size:12px; color:#6b7280; }}

  .task-item {{
    background:white; padding:16px 20px; border-radius:12px;
    display:grid; grid-template-columns:28px 1fr 80px 130px auto;
    gap:14px; align-items:center;
    box-shadow:0 1px 3px rgba(0,0,0,0.05);
    border-left:3px solid #e5e7eb;
    transition:all 0.15s;
  }}
  .task-item:hover {{ transform:translateY(-1px); box-shadow:0 4px 12px rgba(0,0,0,0.08); }}
  .task-item.completed {{ opacity:0.55; }}
  .task-item.completed h3 {{ text-decoration:line-through; color:#6b7280; }}
  .task-item.urgent {{ border-left-color:#e63946; }}
  .task-item.overdue {{ border-left-color:#e63946; }}
  .task-item.upcoming {{ border-left-color:#f59e0b; }}

  .checkbox {{
    width:22px; height:22px; border:2px solid #d1d5db;
    border-radius:6px; display:flex; align-items:center; justify-content:center;
    cursor:pointer; text-decoration:none; color:white;
    font-size:11px; font-weight:700; transition:all 0.15s;
  }}
  .checkbox:hover:not(.checked) {{ border-color:#1a1a1a; }}
  .checkbox.checked {{ background:#10b981; border-color:#10b981; }}

  .task-main h3 {{ font-size:14px; font-weight:500; margin-bottom:4px; }}
  .task-meta {{ font-size:11px; color:#9ca3af; }}
  .badge {{ padding:3px 9px; border-radius:5px; font-size:11px; font-weight:600; white-space:nowrap; }}
  .status-label {{ font-size:11px; font-weight:600; color:#6b7280; }}
  .actions {{ display:flex; gap:6px; }}
  .edit-btn, .delete-btn {{
    padding:5px 10px; border-radius:6px; font-size:11px;
    font-weight:600; border:none; cursor:pointer;
    text-decoration:none; transition:all 0.15s;
  }}
  .edit-btn {{ background:#f3f4f6; color:#374151; }}
  .edit-btn:hover {{ background:#e5e7eb; }}
  .delete-btn {{ background:#fef2f2; color:#dc2626; }}
  .delete-btn:hover {{ background:#fee2e2; }}

  .empty-state {{
    grid-column:1; text-align:center; padding:60px 20px;
    background:white; border-radius:14px;
    box-shadow:0 1px 3px rgba(0,0,0,0.05);
  }}
  .empty-icon {{ font-size:40px; margin-bottom:16px; }}
  .empty-state h3 {{ font-size:16px; font-weight:600; margin-bottom:8px; }}
  .empty-state p {{ font-size:13px; color:#6b7280; }}

  /* SIDEBAR */
  .sidebar {{ position:sticky; top:72px; height:fit-content; display:flex; flex-direction:column; gap:14px; }}
  .stat-card {{
    background:white; padding:20px 24px; border-radius:14px;
    box-shadow:0 1px 3px rgba(0,0,0,0.05); text-align:center;
  }}
  .stat-label {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:#9ca3af; margin-bottom:6px; }}
  .stat-num {{ font-size:40px; font-weight:300; color:#0a0a0a; line-height:1; }}
  .progress-card {{
    background:white; padding:24px; border-radius:14px;
    box-shadow:0 1px 3px rgba(0,0,0,0.05); text-align:center;
  }}
  .ring-wrap {{ width:96px; height:96px; margin:0 auto 12px; }}
  .ring-wrap svg {{ width:100%; height:100%; transform:rotate(-90deg); }}
  .ring-bg {{ fill:none; stroke:#f3f4f6; stroke-width:7; }}
  .ring-fill {{
    fill:none; stroke:{ring_color}; stroke-width:7; stroke-linecap:round;
    stroke-dasharray:282; stroke-dashoffset:{282 - (progress/100*282):.1f};
    transition:stroke-dashoffset 0.6s ease;
  }}
  .progress-pct {{ font-size:22px; font-weight:300; color:{ring_color}; }}

  /* MODAL */
  .modal {{
    display:none; position:fixed; inset:0;
    background:rgba(0,0,0,0.4); z-index:999;
    align-items:center; justify-content:center;
    backdrop-filter:blur(4px);
  }}
  .modal.active {{ display:flex; }}
  .modal-box {{
    background:white; padding:36px; border-radius:16px;
    width:90%; max-width:420px;
    box-shadow:0 24px 64px rgba(0,0,0,0.2);
  }}
  .modal-box h2 {{ font-size:18px; font-weight:700; margin-bottom:20px; }}
  .modal-form {{ display:grid; gap:11px; }}
  .modal-actions {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:20px; }}
  .modal-btn {{ padding:11px; border-radius:8px; border:none; font-weight:600; cursor:pointer; font-size:14px; }}
  .cancel-btn {{ background:#f3f4f6; color:#374151; }}
  .save-btn {{ background:#0a0a0a; color:white; }}

  /* RESPONSIVE */
  @media(max-width:900px) {{
    .page {{ grid-template-columns:1fr; }}
    .sidebar {{ display:grid; grid-template-columns:repeat(4,1fr); position:static; }}
    .task-item {{ grid-template-columns:28px 1fr 70px; }}
    .task-item .status-label, .task-item .actions {{ display:none; }}
  }}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-logo">TASK<span>FLOW</span></div>
  <div class="topbar-right">
    <span class="topbar-date">{date.today().strftime('%B %d, %Y')}</span>
    <a href="/logout" class="logout">Sign out</a>
  </div>
</div>

<div class="page">

  <div>
    <div class="page-header">
      <h1>Your Dashboard</h1>
      <p>Stay on top of every commitment.</p>
    </div>

    <div class="form-card">
      <div class="form-card-title">New task</div>
      <form action="/task/add" method="POST">
        <div class="form-grid">
          <div class="form-full">
            <input type="text" name="title" placeholder="Task title" required />
          </div>
          <div class="form-row">
            <input type="text" name="category" placeholder="Category" required />
            <input type="date" name="due_date" required />
          </div>
          <div class="form-row">
            <select name="priority" required>
              <option value="">Priority</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
            <select name="task_type" required>
              <option value="">Type</option>
              <option value="Work">Work</option>
              <option value="Personal">Personal</option>
            </select>
          </div>
          <div class="form-full">
            <button type="submit" class="btn-add">Add task</button>
          </div>
        </div>
      </form>
    </div>

    <div class="tasks-header">
      <h2>All tasks</h2>
      <span class="tasks-count">{total} task{'s' if total != 1 else ''}</span>
    </div>

    <div class="tasks-list" style="margin-top:12px">
      {tasks_html if tasks_html else '''<div class="empty-state">
        <div class="empty-icon">✅</div>
        <h3>No tasks yet</h3>
        <p>Create your first task using the form above.</p>
      </div>'''}
    </div>
  </div>

  <div class="sidebar">
    <div class="stat-card">
      <div class="stat-label">Total</div>
      <div class="stat-num">{total}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Done</div>
      <div class="stat-num">{completed}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Pending</div>
      <div class="stat-num">{pending}</div>
    </div>
    <div class="progress-card">
      <div class="stat-label">Progress</div>
      <div class="ring-wrap">
        <svg viewBox="0 0 100 100">
          <circle class="ring-bg" cx="50" cy="50" r="45"/>
          <circle class="ring-fill" cx="50" cy="50" r="45"/>
        </svg>
      </div>
      <div class="progress-pct">{progress}%</div>
    </div>
  </div>

</div>

<!-- EDIT MODAL -->
<div id="editModal" class="modal">
  <div class="modal-box">
    <h2>Edit task</h2>
    <form id="editForm" method="POST" action="">
      <div class="modal-form">
        <input type="text" id="editTitle" name="title" placeholder="Title" required />
        <input type="text" id="editCategory" name="category" placeholder="Category" required />
        <input type="date" id="editDueDate" name="due_date" required />
        <select id="editPriority" name="priority" required>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <select id="editTaskType" name="task_type" required>
          <option value="Work">Work</option>
          <option value="Personal">Personal</option>
        </select>
        <div class="modal-actions">
          <button type="button" class="modal-btn cancel-btn" onclick="closeEdit()">Cancel</button>
          <button type="submit" class="modal-btn save-btn">Save changes</button>
        </div>
      </div>
    </form>
  </div>
</div>

<script>
  function openEdit(id, title, category, priority, dueDate, taskType) {{
    document.getElementById('editTitle').value = title;
    document.getElementById('editCategory').value = category;
    document.getElementById('editPriority').value = priority.charAt(0).toUpperCase() + priority.slice(1);
    document.getElementById('editDueDate').value = dueDate;
    document.getElementById('editTaskType').value = taskType.charAt(0).toUpperCase() + taskType.slice(1);
    document.getElementById('editForm').action = '/task/edit/' + id;
    document.getElementById('editModal').classList.add('active');
  }}
  function closeEdit() {{
    document.getElementById('editModal').classList.remove('active');
  }}
  window.onclick = e => {{
    if (e.target === document.getElementById('editModal')) closeEdit();
  }}
</script>
</body>
</html>"""


# ─── Task Routes (auth-gated) ──────────────────────────────────────────────────
def auth_redirect(session):
    if not is_authenticated(session):
        return RedirectResponse("/", status_code=302)
    return None


@app.post("/task/add")
def task_add(
    session: Optional[str] = Cookie(default=None),
    title: str = Form(...), category: str = Form(...),
    priority: str = Form(...), task_type: str = Form(...), due_date: str = Form(...),
):
    global next_task_id
    if not is_authenticated(session):
        return RedirectResponse("/", status_code=302)
    tasks.append({
        "id": next_task_id, "title": title, "category": category,
        "priority": priority, "due_date": due_date,
        "task_type": task_type, "completed": False,
    })
    next_task_id += 1
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/task/complete/{task_id}")
def task_complete(task_id: int, session: Optional[str] = Cookie(default=None)):
    if not is_authenticated(session):
        return RedirectResponse("/", status_code=302)
    for t in tasks:
        if t["id"] == task_id:
            t["completed"] = not t["completed"]
            break
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/task/edit/{task_id}")
def task_edit(
    task_id: int,
    session: Optional[str] = Cookie(default=None),
    title: str = Form(...), category: str = Form(...),
    priority: str = Form(...), due_date: str = Form(...), task_type: str = Form(...),
):
    if not is_authenticated(session):
        return RedirectResponse("/", status_code=302)
    for t in tasks:
        if t["id"] == task_id:
            t.update(title=title, category=category, priority=priority,
                     due_date=due_date, task_type=task_type)
            break
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/task/delete/{task_id}")
def task_delete(task_id: int, session: Optional[str] = Cookie(default=None)):
    global tasks
    if not is_authenticated(session):
        return RedirectResponse("/", status_code=302)
    tasks = [t for t in tasks if t["id"] != task_id]
    return RedirectResponse("/dashboard", status_code=302)
