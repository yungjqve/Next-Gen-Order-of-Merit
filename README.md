# Next Gen Order of Merit

Rankings website for the **PDC Europe Next Gen** dart series.

Live at [next.jqve.dev](https://next.jqve.dev)

## Features

- **Main & Youth Rankings** — full player tables with rank, PPR, prize money
- **Player Profiles** — detailed stats and tournament history with per-event breakdowns
- **Interesting Order** — curated view of selected players
- **Verbände Filter** — filter players by German regional dart association (auto-detected via DDV APIs)
- **Daily Auto-Refresh** — data updates every day at 22:00 CET from DartConnect
- **Responsive Design** — works on desktop and mobile

## Tech Stack

- Python 3.12 / Flask / Jinja2
- APScheduler (background data refresh)
- Gunicorn + Caddy reverse proxy
- DartConnect API + DDV 3k-darts API

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m flask --app main:app run --debug
```

## Project Structure

```
dart_rankings/
  app.py            # Flask app factory, routes, event grouping
  data.py           # In-memory cache, APScheduler, DDV background job
  fetcher.py        # DartConnect + player events API client
  parser.py         # API payload → Player models
  ddv_lookup.py     # Automated Verbände assignment via DDV APIs
  verbande.py       # Verbände JSON persistence
  qualifiers.py     # Qualifier slot selection
  report.py         # Jinja2 template helpers
  templates/        # HTML templates (base, rankings, player, admin)
main.py             # Entry point
scripts/update.sh   # Deployment script
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ADMIN_USER` | `admin` | Admin panel username |
| `ADMIN_PASS` | *(required)* | Admin panel password |
| `DARTCONNECT_COOKIE` | *(empty)* | Optional DartConnect auth cookie |
| `MAIN_URL` | `pdc-next-gen-2026` | Main rankings URL |
| `YOUTH_URL` | `pdc-next-gen-youth-2026` | Youth rankings URL |
| `MAIN_QUAL` | `16` | Main qualifier slots |
| `YOUTH_QUAL` | `4` | Youth qualifier slots |

## License

Private project by [Maximilian Niemecek](https://github.com/yungjqve).
