
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from claude import (
    app, registered_users, sessions, user_tasks,
    hash_password, get_current_user, is_authenticated,
    username_exists, validate_credentials, check_password,
    get_tasks, _task_display_props,
)

client = TestClient(app, follow_redirects=False)


# ── Fixtures & helpers ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_state():
    """Wipe all in-memory stores AND the client cookie jar before every test."""
    registered_users.clear()
    sessions.clear()
    user_tasks.clear()
    client.cookies.clear()    # prevents session leaking between tests
    yield


def reg(username="alice", password="pass123") -> str:
    """Register a user, store the session cookie on the client, return session value."""
    resp = client.post("/register", data={"username": username, "password": password})
    session = resp.cookies.get("session", "")
    client.cookies.set("session", session)  # set once on client, no per-request cookies
    return session


def add_task(title="Buy milk", priority="Low") -> int:
    """Add a task using the client's current session and return its ID."""
    client.post("/task/add", data={
        "title": title, "category": "Work",
        "priority": priority, "task_type": "Work", "due_date": "2099-01-01T10:00",
    })
    return get_tasks("alice")[-1]["id"]


def in_days(n: int) -> str:
    """Return a datetime-local string N days from today."""
    return (date.today() + timedelta(days=n)).strftime("%Y-%m-%dT08:00")


# ══════════════════════════════════════════════════════════════════════════════
# 1. Pure helper functions
# ══════════════════════════════════════════════════════════════════════════════

def test_hash_password():
    # Checks: hash_password returns the password unchanged (no real hashing yet)
    assert hash_password("hello") == "hello"


def test_validate_credentials():
    ok, msg = validate_credentials("alice", "pass123")
    assert ok is True and msg == ""                       # valid input passes

    ok, msg = validate_credentials("a", "pass123")
    assert ok is False and "2 characters" in msg          # username too short

    ok, msg = validate_credentials("alice", "ab")
    assert ok is False and "3 characters" in msg          # password too short

    ok, msg = validate_credentials("ali ce", "pass123")
    assert ok is False and "spaces" in msg                # spaces not allowed


def test_username_exists():
    assert username_exists("alice") is False              # unknown user → False
    registered_users["alice"] = "x"
    assert username_exists("alice") is True               # found after insert
    assert username_exists("ALICE") is True               # lookup is case-insensitive


def test_check_password():
    registered_users["bob"] = hash_password("secret")
    assert check_password("bob", "secret") is True        # correct password passes
    assert check_password("bob", "wrong") is False        # wrong password fails
    assert check_password("nobody", "x") is False         # unknown user always fails


def test_session_helpers():
    sessions["tok"] = "alice"
    assert get_current_user("tok") == "alice"             # valid token → username
    assert get_current_user("bad") is None                # invalid token → None
    assert get_current_user(None) is None                 # None token → None
    assert is_authenticated("tok") is True                # valid session → True
    assert is_authenticated("bad") is False               # invalid session → False


def test_get_tasks():
    assert get_tasks("alice") == []                       # new user starts with no tasks
    get_tasks("alice").append({"id": 1})
    assert get_tasks("alice")[0]["id"] == 1               # list persists across calls


# ══════════════════════════════════════════════════════════════════════════════
# 2. Task display properties (_task_display_props)
# ══════════════════════════════════════════════════════════════════════════════

def mk(due, priority="High", completed=False, title="T", category="Work"):
    return {"due_date": due, "priority": priority,
            "completed": completed, "title": title, "category": category}


def test_task_status_labels():
    assert _task_display_props(mk(in_days(0), completed=True))["status"] == "Completed"   # done task
    assert _task_display_props(mk(in_days(-1)))["status_class"] == "overdue"               # past due date
    assert _task_display_props(mk(in_days(0)))["status"] == "Due today"                    # due today
    assert _task_display_props(mk(in_days(1)))["status"] == "Due tomorrow"                 # one day away
    assert _task_display_props(mk(in_days(7)))["status"] == "7d left"                      # future task


def test_task_priority_colors():
    assert _task_display_props(mk(in_days(1), priority="High"))["color"] == "#dc2626"      # red for high
    assert _task_display_props(mk(in_days(1), priority="Medium"))["color"] == "#f59e0b"    # yellow for medium
    assert _task_display_props(mk(in_days(1), priority="Low"))["color"] == "#10b981"       # green for low


def test_task_html_escaping():
    d = _task_display_props(mk(in_days(1), title='Say "hi"', category="Bob's"))
    assert "&quot;" in d["title_esc"] and '"' not in d["title_esc"]   # double quotes escaped
    assert "&#39;" in d["cat_esc"] and "'" not in d["cat_esc"]        # single quotes escaped


def test_task_bad_date_fallback():
    # Checks: an unparseable date falls back to the raw string instead of crashing
    assert _task_display_props(mk("bad-date"))["due_display"] == "bad-date"


# ══════════════════════════════════════════════════════════════════════════════
# 3. HTTP routes
# ══════════════════════════════════════════════════════════════════════════════

def test_landing_page():
    resp = client.get("/")
    assert resp.status_code == 200                         # page loads
    assert 'action="/register"' in resp.text              # sign-up form present
    assert 'action="/login"' in resp.text                 # sign-in form present


def test_register():
    resp = client.post("/register", data={"username": "alice", "password": "pass123"})
    assert resp.status_code == 302                         # redirects after success
    assert resp.headers["location"] == "/dashboard"       # goes to dashboard
    assert "session" in resp.cookies                      # session cookie is set
    assert username_exists("alice")                       # user is stored in memory


def test_register_errors():
    resp = client.post("/register", data={"username": "a", "password": "pass123"})
    assert "error" in resp.headers["location"]            # short username rejected

    client.post("/register", data={"username": "alice", "password": "pass123"})
    resp = client.post("/register", data={"username": "alice", "password": "other"})
    assert "error" in resp.headers["location"]            # duplicate username rejected


def test_login():
    client.post("/register", data={"username": "alice", "password": "pass123"})
    resp = client.post("/login", data={"username": "alice", "password": "pass123"})
    assert resp.headers["location"] == "/dashboard"       # correct login → dashboard
    assert "session" in resp.cookies                      # new session cookie issued


def test_login_errors():
    client.post("/register", data={"username": "alice", "password": "pass123"})
    resp = client.post("/login", data={"username": "alice", "password": "wrong"})
    assert "error" in resp.headers["location"]            # wrong password rejected

    resp = client.post("/login", data={"username": "ghost", "password": "pass123"})
    assert "error" in resp.headers["location"]            # unknown user rejected


def test_logout():
    session = reg()                                        # also sets client cookie
    resp = client.get("/logout")
    assert resp.headers["location"] == "/"                # redirects to home
    assert session not in sessions                        # session deleted from store


def test_dashboard_auth_guard():
    resp = client.get("/dashboard")                        # no cookie yet → blocked
    assert resp.headers["location"] == "/"                # redirects to home

    reg("bob", "pass123")                                  # sets client cookie
    resp = client.get("/dashboard")
    assert resp.status_code == 200                        # valid session → page loads
    assert "Bob" in resp.text                             # username shown on page
    assert "No tasks yet" in resp.text                    # empty state when no tasks


def test_task_add():
    resp = client.post("/task/add", data={                 # no session in jar yet
        "title": "X", "category": "Y", "priority": "Low",
        "task_type": "Work", "due_date": "2099-01-01T10:00",
    })
    assert resp.headers["location"] == "/"                # no session → redirect home

    reg()                                                  # now log in
    add_task(title="Buy milk")
    assert get_tasks("alice")[0]["title"] == "Buy milk"   # task stored in memory
    assert get_tasks("alice")[0]["completed"] is False    # new task is incomplete
    assert "Buy milk" in client.get("/dashboard").text    # task visible on dashboard


def test_task_complete_toggle():
    reg()
    tid = add_task()
    client.get(f"/task/complete/{tid}")
    assert get_tasks("alice")[0]["completed"] is True     # first click marks done
    client.get(f"/task/complete/{tid}")
    assert get_tasks("alice")[0]["completed"] is False    # second click marks undone


def test_task_edit():
    reg()
    tid = add_task(title="Old", priority="High")
    client.post(f"/task/edit/{tid}", data={
        "title": "New", "category": "Work", "priority": "Low",
        "due_date": "2099-06-01T09:00", "task_type": "Work",
    })
    t = get_tasks("alice")[0]
    assert t["title"] == "New"                            # title was updated
    assert t["priority"] == "Low"                         # priority was updated


def test_task_delete():
    reg()
    id1 = add_task(title="Keep")
    id2 = add_task(title="Gone")
    client.get(f"/task/delete/{id2}")
    remaining = get_tasks("alice")
    assert len(remaining) == 1                            # only one task left
    assert remaining[0]["id"] == id1                      # the right task was kept
