from fastapi import FastAPI, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, date, timedelta
from typing import Optional
import secrets
import hashlib

app = FastAPI()

# ─── Data Storage ─────────────────────────────────────────────────────────────
registered_users: dict = {}
sessions: dict = {}
user_tasks: dict = {}
next_task_id: int = 1


# ─── Auth Helpers ─────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_current_user(session: Optional[str]) -> Optional[str]:
    """Get username from session token"""
    if session is None:
        return None
    return sessions.get(session)


def is_authenticated(session: Optional[str]) -> bool:
    """Check if session is valid"""
    return get_current_user(session) is not None


def username_exists(username: str) -> bool:
    """Check if username is already registered"""
    return username.lower() in registered_users


def validate_credentials(username: str, password: str) -> tuple[bool, str]:
    """Validate username and password format"""
    if not username or len(username) < 2:
        return False, "Username must be at least 2 characters"
    if not password or len(password) < 3:
        return False, "Password must be at least 3 characters"
    if " " in username:
        return False, "Username cannot contain spaces"
    return True, ""


def check_password(username: str, password: str) -> bool:
    """Verify password against stored hash"""
    if username.lower() not in registered_users:
        return False
    h = hash_password(password)
    return registered_users[username.lower()] == h


def get_tasks(username: str) -> list:
    """Get tasks for a user"""
    return user_tasks.setdefault(username.lower(), [])


# ─── Landing / Home Page ──────────────────────────────────────────────────────
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
  }

  html { scroll-behavior: smooth; }

  body {
    font-family: 'Inter', sans-serif;
    background: var(--black);
    color: var(--white);
    min-height: 100vh;
    overflow-x: hidden;
  }

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
  .nav-actions { display: flex; gap: 12px; }
  .nav-cta {
    padding: 9px 22px; border-radius: 8px;
    background: var(--red); color: white;
    font-size: 13px; font-weight: 600; letter-spacing: 0.2px;
    text-decoration: none; transition: background 0.2s;
  }
  .nav-cta:hover { background: var(--red-dark); }
  .nav-cta.secondary {
    background: transparent; border: 1px solid rgba(255,255,255,0.2);
  }
  .nav-cta.secondary:hover { border-color: rgba(255,255,255,0.4); }

  .hero {
    min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
    text-align: center;
    padding: 120px 24px 80px;
    position: relative;
    overflow: hidden;
  }

  .hero::before {
    content: '';
    position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 40%, transparent 100%);
  }

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
  .hero h1 em { font-style: italic; color: var(--red); }

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

  .auth-section {
    padding: 120px 24px;
    display: flex; align-items: center; justify-content: center;
  }
  .auth-card {
    background: var(--gray-1);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px;
    padding: 52px 48px;
    width: 100%; max-width: 420px;
    box-shadow: 0 40px 80px rgba(0,0,0,0.4);
  }
  .auth-card h2 {
    font-family: 'Playfair Display', serif;
    font-size: 28px; font-weight: 700;
    margin-bottom: 8px;
  }
  .auth-card p {
    font-size: 14px; color: var(--gray-5); margin-bottom: 24px;
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

  .auth-btn {
    width: 100%; padding: 14px;
    background: var(--red); border: none; border-radius: 10px;
    color: white; font-size: 15px; font-weight: 600;
    cursor: pointer; margin-top: 8px; transition: all 0.2s;
  }
  .auth-btn:hover { background: var(--red-dark); }

  .toggle-auth {
    text-align: center; margin-top: 20px; font-size: 13px; color: var(--gray-5);
  }
  .toggle-auth a {
    color: var(--red); text-decoration: none; font-weight: 600;
  }
  .toggle-auth a:hover { text-decoration: underline; }

  footer {
    border-top: 1px solid rgba(255,255,255,0.06);
    padding: 32px 48px;
    display: flex; align-items: center; justify-content: space-between;
    color: var(--gray-3); font-size: 13px;
  }
  .footer-logo { font-weight: 700; color: var(--gray-5); }
  .footer-logo span { color: var(--red); }

  @media (max-width: 768px) {
    nav { padding: 16px 20px; }
    .nav-actions { gap: 8px; }
    .nav-cta { padding: 8px 16px; font-size: 12px; }
    .features { padding: 80px 20px; }
    .features-grid { grid-template-columns: 1fr; gap: 2px; }
    .feature:first-child { border-radius: 12px 12px 0 0; }
    .feature:last-child { border-radius: 0 0 12px 12px; }
    .auth-card { padding: 36px 24px; }
    footer { flex-direction: column; gap: 8px; text-align: center; }
  }
</style>
</head>
<body>

<nav>
  <div class="nav-logo">TASK<span>FLOW</span></div>
  <div class="nav-actions">
    <a href="#signup" class="nav-cta secondary">Sign up</a>
    <a href="#signin" class="nav-cta">Sign in</a>
  </div>
</nav>

<section class="hero">
  <div class="hero-content">
    <div class="hero-eyebrow"><span class="dot"></span> Your personal task OS</div>
    <h1>Stop managing tasks.<br>Start <em>owning</em> your time.</h1>
    <p class="hero-sub">Track priorities, deadlines, and progress — all in one clean workspace built for people who take their work seriously.</p>
    <div class="hero-actions">
      <a href="#signup" class="btn-primary">Get started free</a>
      <a href="#features" class="btn-ghost">See what's inside</a>
    </div>
  </div>
</section>

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
      <h3>Time tracking</h3>
      <p>Set exact due dates and times. Color-coded deadlines show urgency at a glance.</p>
    </div>
    <div class="feature">
      <div class="feature-icon">📊</div>
      <h3>Live progress ring</h3>
      <p>A real-time completion ring gives you the honest picture of where you stand today.</p>
    </div>
  </div>
</section>

<section class="auth-section" id="signup">
  <div class="auth-card">
    <h2>Create account</h2>
    <p>Join thousands managing their time better.</p>
    <form method="POST" action="/register">
      <div class="field">
        <label>Username</label>
        <input type="text" name="username" placeholder="Choose a username" autofocus required />
      </div>
      <div class="field">
        <label>Password</label>
        <input type="password" name="password" placeholder="At least 3 characters" required />
      </div>
      <button type="submit" class="auth-btn">Create account →</button>
    </form>
    <div class="toggle-auth">
      Already have an account? <a href="#signin">Sign in</a>
    </div>
  </div>
</section>

<section class="auth-section" id="signin">
  <div class="auth-card">
    <h2>Welcome back</h2>
    <p>Access your dashboard and tasks.</p>
    <form method="POST" action="/login">
      <div class="field">
        <label>Username</label>
        <input type="text" name="username" placeholder="Your username" autofocus required />
      </div>
      <div class="field">
        <label>Password</label>
        <input type="password" name="password" placeholder="Your password" required />
      </div>
      <button type="submit" class="auth-btn">Sign in →</button>
    </form>
    <div class="toggle-auth">
      Don't have an account? <a href="#signup">Sign up</a>
    </div>
  </div>
</section>

<footer>
  <div class="footer-logo">TASK<span>FLOW</span></div>
  <div>Built with FastAPI · Zero clutter · Maximum focus</div>
</footer>

</body>
</html>"""


# ─── Auth Routes ──────────────────────────────────────────────────────────────
@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    """Create a new user account"""
    valid, error = validate_credentials(username, password)
    if not valid:
        return RedirectResponse(f"/?error={error}", status_code=302)
    
    if username_exists(username):
        return RedirectResponse("/?error=Username%20already%20taken", status_code=302)
    
    registered_users[username.lower()] = hash_password(password)
    
    token = secrets.token_hex(32)
    sessions[token] = username.lower()
    
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("session", token, httponly=True, max_age=86400 * 7)
    return resp


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    """Login with existing credentials"""
    if not username_exists(username) or not check_password(username, password):
        return RedirectResponse("/?error=Invalid%20username%20or%20password", status_code=302)
    
    token = secrets.token_hex(32)
    sessions[token] = username.lower()
    
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("session", token, httponly=True, max_age=86400 * 7)
    return resp


@app.get("/logout")
def logout(session: Optional[str] = Cookie(default=None)):
    """Logout and destroy session"""
    if session and session in sessions:
        del sessions[session]
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("session")
    return resp


# ─── Dashboard ────────────────────────────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(session: Optional[str] = Cookie(default=None)):
    """Main dashboard view with dark/light theme support"""
    username = get_current_user(session)
    if not username:
        return RedirectResponse("/", status_code=302)

    tasks = get_tasks(username)
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
            due_dt = datetime.strptime(t["due_date"], "%Y-%m-%dT%H:%M")
            days_left = (due_dt.date() - date.today()).days
            due_display = due_dt.strftime("%b %d · %I:%M %p")
        except:
            days_left = 0
            due_display = t["due_date"]

        if t["completed"]:
            status = "Completed"
            status_class = "completed"
        elif days_left < 0:
            n = abs(days_left)
            status = f"Overdue by {n}d"
            status_class = "overdue"
        elif days_left == 0:
            status = "Due today"
            status_class = "urgent"
        elif days_left == 1:
            status = "Due tomorrow"
            status_class = "upcoming"
        else:
            status = f"{days_left}d left"
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
                <p class="task-meta">{t['category']} · {t['task_type']} · {due_display}</p>
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
  :root {{
    /* Dark theme (navy) */
    --bg-primary: #0f1419;
    --bg-secondary: #1a1f2e;
    --bg-tertiary: #232a3e;
    --text-primary: #f8fafb;
    --text-secondary: #b0b9c6;
    --text-tertiary: #8892a1;
    --border: rgba(255, 255, 255, 0.08);
    --accent: #e63946;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #dc2626;
  }}

  html[data-theme="light"] {{
    --bg-primary: #fefdfb;
    --bg-secondary: #f8f6f0;
    --bg-tertiary: #f0ede4;
    --text-primary: #2d2620;
    --text-secondary: #6b6159;
    --text-tertiary: #8b7d72;
    --border: rgba(45, 38, 32, 0.08);
    --accent: #d84c4c;
    --success: #059669;
    --warning: #d97706;
    --danger: #b91c1c;
  }}

  *, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family:'Inter',sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    transition: background 0.3s, color 0.3s;
  }}

  .topbar {{
    position:fixed; top:0; left:0; right:0; z-index:100;
    background: var(--bg-secondary);
    padding:0 32px;
    display:flex; align-items:center; justify-content:space-between;
    height:56px; border-bottom:1px solid var(--border);
    backdrop-filter: blur(8px);
    transition: background 0.3s;
  }}
  .topbar-logo {{ font-weight:700; font-size:16px; color:var(--text-primary); }}
  .topbar-logo span {{ color:var(--accent); }}
  .topbar-right {{ display:flex; align-items:center; gap:16px; }}
  .topbar-info {{ font-size:13px; color:var(--text-secondary); }}
  
  .theme-toggle {{
    width:40px; height:40px; border-radius:8px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    transition: all 0.2s;
  }}
  .theme-toggle:hover {{
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }}
  
  .logout {{
    padding:7px 16px; border-radius:7px;
    border:1px solid var(--border); color:var(--text-secondary);
    font-size:12px; font-weight:500; text-decoration:none;
    transition:all 0.2s;
  }}
  .logout:hover {{ border-color:var(--text-primary); color:var(--text-primary); }}

  .page {{ max-width:1200px; margin:0 auto; padding:80px 32px 60px; display:grid; grid-template-columns:1fr 280px; gap:40px; }}

  .page-header {{ grid-column:1; margin-bottom:8px; }}
  .page-header h1 {{
    font-family:'Playfair Display',serif;
    font-size:36px; font-weight:700; letter-spacing:-0.5px;
    margin-bottom:6px; color: var(--text-primary);
  }}
  .page-header p {{ font-size:14px; color:var(--text-secondary); }}

  .form-card {{
    grid-column:1; background:var(--bg-secondary); padding:28px 32px;
    border-radius:14px; margin-bottom:32px;
    border: 1px solid var(--border);
    box-shadow:0 1px 3px rgba(0,0,0,0.05);
    transition: background 0.3s;
  }}
  .form-card-title {{ font-size:13px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.6px; margin-bottom:20px; }}
  .form-grid {{ display:grid; gap:12px; }}
  .form-row {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
  .form-full {{ grid-column:1/-1; }}
  input[type=text], input[type=datetime-local], select {{
    width:100%; padding:10px 14px;
    border:1px solid var(--border); border-radius:8px;
    font-size:14px; font-family:'Inter',sans-serif;
    color: var(--text-primary);
    background: var(--bg-tertiary);
    transition:border-color 0.2s, background 0.3s;
  }}
  input[type=text]:focus, input[type=datetime-local]:focus, select:focus {{
    outline:none; border-color:var(--accent);
    box-shadow:0 0 0 3px rgba(230,57,70,0.1);
  }}
  .btn-add {{
    width:100%; padding:11px; background:var(--accent); color:white;
    border:none; border-radius:8px; font-weight:600; font-size:14px;
    cursor:pointer; transition:opacity 0.2s;
  }}
  .btn-add:hover {{ opacity:0.85; }}

  .tasks-list {{ grid-column:1; display:flex; flex-direction:column; gap:10px; }}
  .tasks-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; }}
  .tasks-header h2 {{ font-size:15px; font-weight:600; color: var(--text-primary); }}
  .tasks-count {{ font-size:12px; color:var(--text-secondary); }}

  .task-item {{
    background:var(--bg-secondary); padding:16px 20px; border-radius:12px;
    display:grid; grid-template-columns:28px 1fr 80px 130px auto;
    gap:14px; align-items:center;
    border-left:3px solid var(--border);
    transition:all 0.15s;
  }}
  .task-item:hover {{ transform:translateY(-1px); border-left-color: var(--accent); }}
  .task-item.completed {{ opacity:0.5; }}
  .task-item.completed h3 {{ text-decoration:line-through; color:var(--text-tertiary); }}
  .task-item.urgent {{ border-left-color:var(--danger); }}
  .task-item.overdue {{ border-left-color:var(--danger); }}
  .task-item.upcoming {{ border-left-color:var(--warning); }}

  .checkbox {{
    width:22px; height:22px; border:2px solid var(--border);
    border-radius:6px; display:flex; align-items:center; justify-content:center;
    cursor:pointer; text-decoration:none; color:white;
    font-size:11px; font-weight:700; transition:all 0.15s;
  }}
  .checkbox:hover:not(.checked) {{ border-color:var(--text-primary); }}
  .checkbox.checked {{ background:var(--success); border-color:var(--success); }}

  .task-main h3 {{ font-size:14px; font-weight:500; margin-bottom:4px; color: var(--text-primary); }}
  .task-meta {{ font-size:11px; color:var(--text-tertiary); }}
  .badge {{ padding:3px 9px; border-radius:5px; font-size:11px; font-weight:600; white-space:nowrap; }}
  .status-label {{ font-size:11px; font-weight:600; color:var(--text-secondary); }}
  .actions {{ display:flex; gap:6px; }}
  .edit-btn, .delete-btn {{
    padding:5px 10px; border-radius:6px; font-size:11px;
    font-weight:600; border:none; cursor:pointer;
    text-decoration:none; transition:all 0.15s;
  }}
  .edit-btn {{ background:var(--bg-tertiary); color:var(--text-primary); }}
  .edit-btn:hover {{ background: var(--border); }}
  .delete-btn {{ background: rgba(220,38,38,0.15); color:var(--danger); }}
  .delete-btn:hover {{ background: rgba(220,38,38,0.25); }}

  .empty-state {{
    grid-column:1; text-align:center; padding:60px 20px;
    background:var(--bg-secondary); border-radius:14px;
    border: 1px solid var(--border);
  }}
  .empty-icon {{ font-size:40px; margin-bottom:16px; }}
  .empty-state h3 {{ font-size:16px; font-weight:600; margin-bottom:8px; color: var(--text-primary); }}
  .empty-state p {{ font-size:13px; color:var(--text-secondary); }}

  .sidebar {{ position:sticky; top:72px; height:fit-content; display:flex; flex-direction:column; gap:14px; }}
  .stat-card {{
    background:var(--bg-secondary); padding:20px 24px; border-radius:14px;
    border: 1px solid var(--border);
    text-align:center;
  }}
  .stat-label {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:var(--text-tertiary); margin-bottom:6px; }}
  .stat-num {{ font-size:40px; font-weight:300; color:var(--text-primary); line-height:1; }}
  .progress-card {{
    background:var(--bg-secondary); padding:24px; border-radius:14px;
    border: 1px solid var(--border);
    text-align:center;
  }}
  .ring-wrap {{ width:96px; height:96px; margin:0 auto 12px; }}
  .ring-wrap svg {{ width:100%; height:100%; transform:rotate(-90deg); }}
  .ring-bg {{ fill:none; stroke:var(--border); stroke-width:7; }}
  .ring-fill {{
    fill:none; stroke:{ring_color}; stroke-width:7; stroke-linecap:round;
    stroke-dasharray:282; stroke-dashoffset:{282 - (progress/100*282):.1f};
    transition:stroke-dashoffset 0.6s ease;
  }}
  .progress-pct {{ font-size:22px; font-weight:300; color:{ring_color}; }}

  .modal {{
    display:none; position:fixed; inset:0;
    background:rgba(0,0,0,0.5); z-index:999;
    align-items:center; justify-content:center;
    backdrop-filter:blur(4px);
  }}
  .modal.active {{ display:flex; }}
  .modal-box {{
    background:var(--bg-secondary); padding:36px; border-radius:16px;
    width:90%; max-width:420px;
    border: 1px solid var(--border);
    box-shadow:0 24px 64px rgba(0,0,0,0.2);
  }}
  .modal-box h2 {{ font-size:18px; font-weight:700; margin-bottom:20px; color: var(--text-primary); }}
  .modal-form {{ display:grid; gap:11px; }}
  .modal-actions {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:20px; }}
  .modal-btn {{ padding:11px; border-radius:8px; border:none; font-weight:600; cursor:pointer; font-size:14px; }}
  .cancel-btn {{ background:var(--bg-tertiary); color:var(--text-primary); }}
  .save-btn {{ background:var(--accent); color:white; }}

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
    <span class="topbar-info">👤 {username}</span>
    <span class="topbar-info">{date.today().strftime('%b %d, %Y')}</span>
    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">🌙</button>
    <a href="/logout" class="logout">Sign out</a>
  </div>
</div>

<div class="page">
  <div>
    <div class="page-header">
      <h1>Hey, {username.capitalize()} 👋</h1>
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
            <input type="datetime-local" name="due_date" required />
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
            <button type="submit" class="btn-add">Add task →</button>
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
        <p>Create your first task using the form above and start tracking your time.</p>
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

<div id="editModal" class="modal">
  <div class="modal-box">
    <h2>Edit task</h2>
    <form id="editForm" method="POST" action="">
      <div class="modal-form">
        <input type="text" id="editTitle" name="title" placeholder="Title" required />
        <input type="text" id="editCategory" name="category" placeholder="Category" required />
        <input type="datetime-local" id="editDueDate" name="due_date" required />
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
  // Theme toggle
  function toggleTheme() {{
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon();
  }}

  function updateThemeIcon() {{
    const theme = document.documentElement.getAttribute('data-theme') || 'dark';
    const btn = document.querySelector('.theme-toggle');
    btn.textContent = theme === 'dark' ? '☀️' : '🌙';
  }}

  // Load saved theme on page load
  document.addEventListener('DOMContentLoaded', () => {{
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon();
  }});

  // Modal functions
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


# ─── Task Routes ──────────────────────────────────────────────────────────────
@app.post("/task/add")
def task_add(
    session: Optional[str] = Cookie(default=None),
    title: str = Form(...),
    category: str = Form(...),
    priority: str = Form(...),
    task_type: str = Form(...),
    due_date: str = Form(...),
):
    """Add a new task"""
    global next_task_id
    username = get_current_user(session)
    if not username:
        return RedirectResponse("/", status_code=302)
    
    get_tasks(username).append({
        "id": next_task_id,
        "title": title,
        "category": category,
        "priority": priority,
        "due_date": due_date,
        "task_type": task_type,
        "completed": False,
    })
    next_task_id += 1
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/task/complete/{task_id}")
def task_complete(task_id: int, session: Optional[str] = Cookie(default=None)):
    """Toggle task completion"""
    username = get_current_user(session)
    if not username:
        return RedirectResponse("/", status_code=302)
    
    for t in get_tasks(username):
        if t["id"] == task_id:
            t["completed"] = not t["completed"]
            break
    
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/task/edit/{task_id}")
def task_edit(
    task_id: int,
    session: Optional[str] = Cookie(default=None),
    title: str = Form(...),
    category: str = Form(...),
    priority: str = Form(...),
    due_date: str = Form(...),
    task_type: str = Form(...),
):
    """Edit an existing task"""
    username = get_current_user(session)
    if not username:
        return RedirectResponse("/", status_code=302)
    
    for t in get_tasks(username):
        if t["id"] == task_id:
            t.update(
                title=title,
                category=category,
                priority=priority,
                due_date=due_date,
                task_type=task_type
            )
            break
    
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/task/delete/{task_id}")
def task_delete(task_id: int, session: Optional[str] = Cookie(default=None)):
    """Delete a task"""
    username = get_current_user(session)
    if not username:
        return RedirectResponse("/", status_code=302)
    
    user_tasks[username] = [t for t in get_tasks(username) if t["id"] != task_id]
    return RedirectResponse("/dashboard", status_code=302)
