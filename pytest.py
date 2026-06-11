"""Tests for the TaskFlow application (clone.py)."""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from clone import (
    app, registered_users, sessions, user_tasks,
    hash_password, get_current_user, is_authenticated,
    username_exists, validate_credentials, check_password,
    get_tasks, _task_display_props,
)

client = TestClient(app, follow_redirects=False)


# ── Fixtures & helpers ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_state():
    """Reset all in-memory data and clear cookies before every test so tests don't bleed into each other."""
    registered_users.clear()   # wipe all registered accounts
    sessions.clear()           # wipe all active login sessions
    user_tasks.clear()         # wipe all stored tasks
    client.cookies.clear()     # clear session cookie so no test inherits a login
    yield


def reg(username="alice", password="pass123") -> str:
    """Register a user via the /register route and set the session cookie on the client."""
    resp = client.post("/register", data={"username": username, "password": password})
    session = resp.cookies.get("session", "")
    client.cookies.set("session", session)  # store cookie once — no need to pass per-request
    return session


def add_task(title="Buy milk", priority="Low") -> int:
    """Post a new task using whatever session cookie is currently on the client."""
    client.post("/task/add", data={
        "title": title, "category": "Work",
        "priority": priority, "task_type": "Work", "due_date": "2099-01-01T10:00",
    })
    return get_tasks("alice")[-1]["id"]  # return the id of the task just added


def in_days(n: int) -> str:
    """Return a datetime-local string that is N days from today (used to build test tasks)."""
    return (date.today() + timedelta(days=n)).strftime("%Y-%m-%dT08:00")


# ══════════════════════════════════════════════════════════════════════════════
# 1. Pure helper functions
# ══════════════════════════════════════════════════════════════════════════════

def test_hash_password():
    # Checks: hash_password currently stores passwords as plain text (no real hashing)
    assert hash_password("hello") == "hello"


def test_validate_credentials():
    # Checks: validate_credentials rejects bad input and accepts good input
    ok, msg = validate_credentials("alice", "pass123")
    assert ok is True and msg == ""                       # valid username + password → passes

    ok, msg = validate_credentials("a", "pass123")
    assert ok is False and "2 characters" in msg          # username too short → fails

    ok, msg = validate_credentials("alice", "ab")
    assert ok is False and "3 characters" in msg          # password too short → fails

    ok, msg = validate_credentials("ali ce", "pass123")
    assert ok is False and "spaces" in msg                # space in username → fails


def test_username_exists():
    # Checks: username lookup is case-insensitive and reflects live data
    assert username_exists("alice") is False              # user doesn't exist yet
    registered_users["alice"] = "x"                      # manually insert user
    assert username_exists("alice") is True               # now it exists
    assert username_exists("ALICE") is True               # uppercase version also found


def test_check_password():
    # Checks: check_password correctly validates and rejects passwords
    registered_users["bob"] = hash_password("secret")
    assert check_password("bob", "secret") is True        # correct password → passes
    assert check_password("bob", "wrong") is False        # wrong password → fails
    assert check_password("nobody", "x") is False         # unknown user always → fails


def test_session_helpers():
    # Checks: get_current_user and is_authenticated work correctly with valid and invalid tokens
    sessions["tok"] = "alice"
    assert get_current_user("tok") == "alice"             # valid token → returns username
    assert get_current_user("bad") is None                # unknown token → None
    assert get_current_user(None) is None                 # None token → None (no crash)
    assert is_authenticated("tok") is True                # valid token → authenticated
    assert is_authenticated("bad") is False               # invalid token → not authenticated


def test_get_tasks():
    # Checks: get_tasks creates an empty list for new users and persists mutations
    assert get_tasks("alice") == []                       # brand new user → empty list
    get_tasks("alice").append({"id": 1})
    assert get_tasks("alice")[0]["id"] == 1               # appended item is still there


# ══════════════════════════════════════════════════════════════════════════════
# 2. Task display properties (_task_display_props)
# ══════════════════════════════════════════════════════════════════════════════

def mk(due, priority="High", completed=False, title="T", category="Work"):
    """Build a minimal task dict for testing _task_display_props."""
    return {"due_date": due, "priority": priority,
            "completed": completed, "title": title, "category": category}


def test_task_status_labels():
    # Checks: each due-date scenario produces the correct status text and CSS class
    assert _task_display_props(mk(in_days(0), completed=True))["status"] == "Completed"   # completed task
    assert _task_display_props(mk(in_days(-1)))["status_class"] == "overdue"               # past due date → red class
    assert _task_display_props(mk(in_days(0)))["status"] == "Due today"                    # due today → urgent
    assert _task_display_props(mk(in_days(1)))["status"] == "Due tomorrow"                 # one day left
    assert _task_display_props(mk(in_days(7)))["status"] == "7d left"                      # future task shows countdown


def test_task_priority_colors():
    # Checks: priority level maps to the correct badge colour
    assert _task_display_props(mk(in_days(1), priority="High"))["color"] == "#dc2626"      # High → red
    assert _task_display_props(mk(in_days(1), priority="Medium"))["color"] == "#f59e0b"    # Medium → amber
    assert _task_display_props(mk(in_days(1), priority="Low"))["color"] == "#10b981"       # Low → green


def test_task_html_escaping():
    # Checks: special characters in title and category are HTML-escaped to prevent XSS
    d = _task_display_props(mk(in_days(1), title='Say "hi"', category="Bob's"))
    assert "&quot;" in d["title_esc"] and '"' not in d["title_esc"]   # " → &quot;
    assert "&#39;" in d["cat_esc"] and "'" not in d["cat_esc"]        # ' → &#39;


def test_task_bad_date_fallback():
    # Checks: a task with an unparseable date string falls back to showing the raw string (no crash)
    assert _task_display_props(mk("bad-date"))["due_display"] == "bad-date"


def test_overdue_days_count():
    # Checks: the overdue label includes the exact number of days past due
    props = _task_display_props(mk(in_days(-3)))           # task was due 3 days ago
    assert props["status"] == "Overdue by 3d"             # label shows the correct count
    assert props["status_class"] == "overdue"             # CSS class is also overdue


def test_completed_task_css_class():
    # Checks: a completed task always gets the "completed" CSS class, regardless of due date
    props = _task_display_props(mk(in_days(-5), completed=True))  # overdue but marked done
    assert props["status"] == "Completed"                 # completion overrides overdue status
    assert props["status_class"] == "completed"           # CSS class reflects completion, not overdue


def test_unknown_priority_fallback():
    # Checks: a task with an unrecognised priority level gets the default grey colour instead of crashing
    props = _task_display_props(mk(in_days(1), priority="Extreme"))
    assert props["color"] == "#666"                       # fallback grey colour for unknown priority


# ══════════════════════════════════════════════════════════════════════════════
# 3. HTTP routes
# ══════════════════════════════════════════════════════════════════════════════

def test_landing_page():
    # Checks: the home page loads and contains both the register and login forms
    resp = client.get("/")
    assert resp.status_code == 200                         # page renders successfully
    assert 'action="/register"' in resp.text              # sign-up form is present
    assert 'action="/login"' in resp.text                 # sign-in form is present


def test_register():
    # Checks: a valid registration redirects to the dashboard and sets a session cookie
    resp = client.post("/register", data={"username": "alice", "password": "pass123"})
    assert resp.status_code == 302                         # success → redirect
    assert resp.headers["location"] == "/dashboard"       # lands on dashboard
    assert "session" in resp.cookies                      # session cookie is issued
    assert username_exists("alice")                       # account exists in memory


def test_register_errors():
    # Checks: short usernames and duplicate accounts are rejected
    resp = client.post("/register", data={"username": "a", "password": "pass123"})
    assert "error" in resp.headers["location"]            # username too short → error

    client.post("/register", data={"username": "alice", "password": "pass123"})
    resp = client.post("/register", data={"username": "alice", "password": "other"})
    assert "error" in resp.headers["location"]            # duplicate username → error


def test_login():
    # Checks: correct credentials redirect to dashboard and issue a session cookie
    client.post("/register", data={"username": "alice", "password": "pass123"})
    resp = client.post("/login", data={"username": "alice", "password": "pass123"})
    assert resp.headers["location"] == "/dashboard"       # successful login → dashboard
    assert "session" in resp.cookies                      # fresh session cookie issued


def test_login_errors():
    # Checks: wrong password and unknown users are both rejected
    client.post("/register", data={"username": "alice", "password": "pass123"})
    resp = client.post("/login", data={"username": "alice", "password": "wrong"})
    assert "error" in resp.headers["location"]            # wrong password → error

    resp = client.post("/login", data={"username": "ghost", "password": "pass123"})
    assert "error" in resp.headers["location"]            # unknown user → error


def test_logout():
    # Checks: logout redirects home and removes the session from the store
    session = reg()
    resp = client.get("/logout")
    assert resp.headers["location"] == "/"                # redirects to home page
    assert session not in sessions                        # session token deleted


def test_dashboard_auth_guard():
    # Checks: unauthenticated requests are blocked; authenticated requests see the dashboard
    resp = client.get("/dashboard")
    assert resp.headers["location"] == "/"                # no cookie → kicked to home

    reg("bob", "pass123")                                  # log in as bob
    resp = client.get("/dashboard")
    assert resp.status_code == 200                        # valid session → page loads
    assert "Bob" in resp.text                             # username displayed on page
    assert "No tasks yet" in resp.text                    # empty task list shown


def test_task_add():
    # Checks: unauthenticated add is blocked; authenticated add stores the task and shows it
    resp = client.post("/task/add", data={                 # no session cookie yet
        "title": "X", "category": "Y", "priority": "Low",
        "task_type": "Work", "due_date": "2099-01-01T10:00",
    })
    assert resp.headers["location"] == "/"                # not logged in → redirect home

    reg()                                                  # now log in as alice
    add_task(title="Buy milk")
    assert get_tasks("alice")[0]["title"] == "Buy milk"   # task saved in memory
    assert get_tasks("alice")[0]["completed"] is False    # new task starts as incomplete
    assert "Buy milk" in client.get("/dashboard").text    # task appears on dashboard


def test_task_complete_toggle():
    # Checks: hitting /task/complete toggles the completed flag each time
    reg()
    tid = add_task()
    client.get(f"/task/complete/{tid}")
    assert get_tasks("alice")[0]["completed"] is True     # first click → done
    client.get(f"/task/complete/{tid}")
    assert get_tasks("alice")[0]["completed"] is False    # second click → undone


def test_task_edit():
    # Checks: editing a task updates its fields in memory
    reg()
    tid = add_task(title="Old", priority="High")
    client.post(f"/task/edit/{tid}", data={
        "title": "New", "category": "Work", "priority": "Low",
        "due_date": "2099-06-01T09:00", "task_type": "Work",
    })
    t = get_tasks("alice")[0]
    assert t["title"] == "New"                            # title updated
    assert t["priority"] == "Low"                         # priority updated


def test_task_delete():
    # Checks: deleting a task removes only that task and leaves the rest intact
    reg()
    id1 = add_task(title="Keep")
    id2 = add_task(title="Gone")
    client.get(f"/task/delete/{id2}")
    remaining = get_tasks("alice")
    assert len(remaining) == 1                            # only one task remains
    assert remaining[0]["id"] == id1                      # the correct task was kept


def test_multiple_tasks_on_dashboard():
    # Checks: adding several tasks stores them all and shows them all on the dashboard
    reg()
    add_task(title="Task One")
    add_task(title="Task Two")
    add_task(title="Task Three")
    assert len(get_tasks("alice")) == 3                   # all three tasks stored in memory
    page = client.get("/dashboard").text
    assert "Task One" in page                             # first task visible on page
    assert "Task Two" in page                             # second task visible on page
    assert "Task Three" in page                           # third task visible on page


def test_task_type_stored():
    # Checks: the task_type field is saved correctly for both Work and Personal tasks
    reg()
    client.post("/task/add", data={
        "title": "Work thing", "category": "Dev", "priority": "High",
        "task_type": "Work", "due_date": "2099-01-01T10:00",
    })
    client.post("/task/add", data={
        "title": "Personal thing", "category": "Life", "priority": "Low",
        "task_type": "Personal", "due_date": "2099-01-01T10:00",
    })
    tasks = get_tasks("alice")
    assert tasks[0]["task_type"] == "Work"                # first task saved as Work type
    assert tasks[1]["task_type"] == "Personal"            # second task saved as Personal type


def test_login_case_insensitive():
    # Checks: usernames are stored in lowercase so "Alice" and "alice" refer to the same account
    client.post("/register", data={"username": "alice", "password": "pass123"})
    resp = client.post("/login", data={"username": "ALICE", "password": "pass123"})
    assert resp.headers["location"] == "/dashboard"       # uppercase login still succeeds
    assert "session" in resp.cookies                      # session cookie issued normally
