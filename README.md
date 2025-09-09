# Movie ELO

A tiny Flask app to rank movies with the ELO system. Users pick a favorite between two posters; ratings update and a leaderboard shows the results. Includes keyboard shortcuts, subtle animations, and a simple admin mode for adding and deleting movies.

## Features
- Compare two random movies; ELO updates per match
- Larger posters and clean layout with a shared base + CSS
- Actions: It’s a tie, or Skip (haven’t seen at least one)
- Keyboard shortcuts:
  - Left/Right arrows: pick left/right movie
  - Up arrow: tie
  - Down arrow: skip
- ELO UX:
  - Hidden until selection, then smoothly revealed
  - “Points transfer” animation from loser to winner
  - Color-coded gain/loss feedback
- Next match excludes both movies from the previous match (when 3+ movies exist)
- Leaderboard with top‑3 podium and confetti; rest listed by rank
- Admin login (session-based):
  - Show Add Movie tab only for admins
  - Delete buttons for movies (including on the podium)
  - Server-side protection for creating/deleting

## Quick Start
Prereqs: Python 3.9+ (3.10+ recommended)

```bash
# 1) Create and activate a virtualenv (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Configure environment
cp .env.example .env
# edit .env and set SECRET_KEY and ADMIN_PASSWORD

# 4) Run the app
python server.py
# Open http://127.0.0.1:5000
```

To deploy under WSGI:
```bash
gunicorn wsgi:app -b 0.0.0.0:8000 --workers 2
```

## Environment Variables
Loaded via `.env` (python-dotenv):
- `SECRET_KEY`: Flask session secret (required in production)
- `ADMIN_PASSWORD`: Password for admin login
- `ADD_MOVIE_PASSWORD`: Optional legacy fallback used by login if `ADMIN_PASSWORD` is unset

## App Structure
- `server.py`: Flask app, routes, DB access, ELO logic
- `wsgi.py`: WSGI entrypoint (`app`)
- `templates/`
  - `base.html`: shared layout and navigation
  - `match.html`: match screen (animations, keyboard shortcuts)
  - `leaderboard.html`: podium (top 3 + confetti) and table (rank 4+)
  - `add_movie.html`: add movie form (admin only)
  - `login.html`: admin login form
- `static/style.css`: shared styles
- `movies.db`: SQLite database (auto-created)

## Database
SQLite (`movies.db`) with two tables (auto-created at startup):
- `movies`:
  - `id INTEGER PRIMARY KEY`
  - `name TEXT NOT NULL`
  - `image_url TEXT`
  - `elo_rating INTEGER DEFAULT 1500`
  - `matches_played INTEGER DEFAULT 0`
  - `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
- `matches`:
  - `id INTEGER PRIMARY KEY`
  - `winner_id INTEGER` / `loser_id INTEGER`
  - `winner_elo_before/after`, `loser_elo_before/after`
  - `match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

## Key Routes
- `GET /` → redirect to `/match`
- `GET /match` → show two random movies (avoids last pair when possible)
- `POST /vote` → body `{winner_id, loser_id}`; updates ELO and logs match
- `POST /tie` → body `{movie_a_id, movie_b_id}`; updates both as draw
- `POST /skip` → acknowledge without rating change
- `GET /see` → leaderboard (top‑3 podium + ranks 4+ table)
- `GET /new` (admin) → add movie form
- `POST /add` (admin) → insert movie
- `POST /delete/<id>` (admin) → delete a movie and related matches
- `GET|POST /login` → session-based admin login
- `POST /logout` → end admin session

## Using Admin Mode
1. Set `ADMIN_PASSWORD` in `.env` and restart
2. Click “Log in” (top right) and enter the password
3. Admins see:
   - “Add Movie” tab
   - Trash buttons on leaderboard (including top‑3 podium)
   - An “Admin” badge in the nav

## Notes
- ELO K-factor: 32 (client animations mirror server calcs for visual consistency)
- Images: provide direct poster URLs when adding movies
- Security: server always checks `session['admin']` for protected actions; hiding buttons is not the only control

## License
No license specified by default. Add one if you plan to share publicly.

