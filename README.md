# WEC Endurance Manager

A browser-based **FIA World Endurance Championship** team-principal game. Take charge of a
Hypercar or LMGT3 squad, sign drivers, manage your budget, run the eight-round WEC calendar
from the Qatar 1812 km to the Bahrain finale, and chase the Drivers', Teams' and Manufacturers'
titles.

It is a racing reimagining of a classic sports-manager loop: choose a team → build a squad →
run a season of races → fight for the championship → recruit young drivers → roll into the next
season as drivers age, develop and retire.

## Requirements

- Python **3.10+**
- pip

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file (optional):

```env
FLASK_SECRET_KEY=your-secret-key
ENABLE_SCHEDULER=true
ADMIN_ENABLED=false
```

No API key is required. The driver/team grid ships as a curated dataset (`data/grid.json`),
so the app runs fully offline.

## Running locally

```bash
python app.py
```

Open http://127.0.0.1:5000/

## Windows desktop build (.exe)

Package the game as a standalone Windows app with [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller wec-manager.spec
```

The executable and bundled assets land in `dist/WEC-Endurance-Manager/`. Run
`WEC-Endurance-Manager.exe` — it starts the local server and opens your browser.

Season saves and grid cache updates are stored under
`%APPDATA%\WEC-Endurance-Manager\` (not beside the `.exe`).

You can also use the launcher in development:

```bash
python launcher.py
```

## Refreshing the grid

Driver and team data is cached in `data/grid.json`. Rebuild the curated grid (synthetic season
form, fresh ratings and attributes) with:

```bash
python fetcher.py
```

Or click **Refresh Grid** on the Browse page while the app is running.

The scheduler rebuilds the grid once per day when `ENABLE_SCHEDULER=true` (local dev only).

## Game flow

1. **Choose your team** — pick a Hypercar or LMGT3 squad and a difficulty.
2. **Dashboard** — squad rating, lead drivers, budget.
3. **My Squad** — driver lineup, contracts, reserve/development drivers, extensions, releases.
4. **Driver Market** — sign free-agent drivers to fill seats.
5. **Transfers** — swap drivers and young-driver test slots with rival teams.
6. **Season** — the eight-round calendar, championship standings per class, sim a round / a
   double-header / to the transfer deadline / the rest of the season.
7. **Season Finale** — run the Bahrain finale to crown the champions.
8. **Season Review** — awards, title winners, statistical leaders.
9. **Young Driver Programme** — a reverse-order rookie draft to build your academy.
10. **Off-season** — advance the calendar; drivers age, develop and retire.

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_SECRET_KEY` | No | `dev` | Flask session secret |
| `ENABLE_SCHEDULER` | No | `true` | Daily grid rebuild (disable on hosted deploys) |
| `ADMIN_ENABLED` | No | `false` | Localhost-only admin tools |
| `ADMIN_TOKEN` | No | — | Optional token for the admin panel |

## Project structure

```
app.py            Flask routes
admin.py          Localhost-only admin panel
fetcher.py        Builds the cached grid from the curated dataset
cache.py          JSON file cache
wec_data.py       Curated teams + drivers + calendar
ratings.py        Driver & team performance ratings
attributes.py     Driver attributes, development, aging
simulation.py     Race-weekend simulation (qualifying + race)
season.py         Calendar, standings, sim, finale, off-season
contracts.py      Budget cap, salaries, driver-market offers
trade.py          Driver transfer engine
draft.py          Young Driver Programme (rookie draft)
roster.py         Squad limits, reserve drivers, releases
injuries.py       Reliability & driver-availability events
gm_personalities.py  Team-principal archetypes
news.py / news_templates.py  Paddock news ticker
year_end_report.py   End-of-season awards report
difficulty.py     Difficulty presets
season_store.py   Per-season save files
scheduler.py      Daily grid refresh
data/grid.json    Cached driver/team grid
templates/        HTML views
```

## Disclaimer

This is an unofficial fan-made simulation game for entertainment. It is not affiliated with,
endorsed by, or associated with the FIA, the ACO, or the FIA World Endurance Championship.
Team and manufacturer names are used for identification purposes only and remain the property
of their respective owners.
