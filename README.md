# Taskflow

A professional task tracker with a landing page, password-protected dashboard, and full CRUD. Built with FastAPI — runs as a single process, ready for Railway.

## Local setup

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://localhost:8000`

Default password: `taskflow2024`

## Set a custom password

Use an environment variable:

```bash
APP_PASSWORD=yourpassword uvicorn main:app --reload
```

## Deploy to Railway

### Method 1 — GitHub (recommended)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Select your repo
4. Railway auto-detects the `Procfile` and builds it
5. Go to **Variables** tab → add `APP_PASSWORD` = your chosen password
6. Done — Railway gives you a public URL

### Method 2 — Railway CLI

```bash
npm install -g @railway/cli
railway login
railway init
railway up
railway variables set APP_PASSWORD=yourpassword
```

## Project structure

```
main.py          # Single FastAPI app: landing + auth + dashboard + tasks
requirements.txt
Procfile         # Railway start command
railway.toml     # Railway config
```

## Routes

| Route | Description |
|-------|-------------|
| `GET /` | Landing page |
| `POST /login` | Password auth → sets session cookie |
| `GET /logout` | Clears session |
| `GET /dashboard` | Task dashboard (requires auth) |
| `POST /task/add` | Add task |
| `GET /task/complete/{id}` | Toggle complete |
| `POST /task/edit/{id}` | Edit task |
| `GET /task/delete/{id}` | Delete task |

## Notes

- Tasks are stored in memory — they reset on redeploy. To persist data, add a database (PostgreSQL on Railway is one click).
- Sessions are in-memory too; they clear on restart. Fine for personal use.
