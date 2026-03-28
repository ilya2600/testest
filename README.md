# MiniSocial (Final Project)

Simple social media web app for the course final project.

## Features

- Create a post
- Read posts in a feed
- Edit a post
- Delete a post
- Like a post
- Data stored in SQLite (`minisocial.db`)

## Stack

- Python + Flask
- SQLite
- HTML/CSS/JavaScript

## Run locally

1. Open terminal in this folder:
   - `cd final_project`
2. Create and activate virtual environment (recommended):
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Create env file:
   - copy `.env.example` to `.env`
   - set at least:
     - `FLASK_SECRET_KEY`
     - `MASTER_ADMIN_USERNAME`
     - `MASTER_ADMIN_PASSWORD`
5. Start app:
   - `python app.py`
6. Open browser:
   - `http://127.0.0.1:5000`

## Demo seed content (optional)

For deployments or local testing, you can fill the database with fake users (`demo_seed_00`, …), random 8×8 avatars, posts with PNG attachments, and random likes.

1. In `.env`, set `DEMO_SEED_ENABLED=true` (and optionally `DEMO_SEED_USERS=8`).
2. From `final_project`, run: `python seed_demo.py`
3. Log in as any demo user; the shared password is **`DemoSeed123!`** (set in `seed_demo.py`).

The script exits immediately if `DEMO_SEED_ENABLED` is not true. After a successful run, it records a flag in `app_settings` so it **skips** on the next run unless you set **`DEMO_SEED_FORCE=true`** (which deletes existing `demo_seed_*` users and re-seeds).

## Project layout

- `app.py` — entry point: `create_app()` then `app.run(debug=True)` when run as main
- `minisocial/` — application package: `create_app()` calls `init_db()` so Gunicorn and `python app.py` both get migrations; also `config`, `db`, `auth`, `services/feed`, `routes/`
- `seed_demo.py` — optional demo data seeder (see above)
- `templates/` — HTML pages
- `static/style.css` — styles
- `static/app.js` — simple client-side validation
