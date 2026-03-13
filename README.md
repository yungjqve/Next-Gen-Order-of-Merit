# next.jqve.dev - DartConnect Rankings

Flask web app serving PDC Next Gen dart player rankings at:
- `https://next.jqve.dev`

Data is fetched from DartConnect on startup and refreshed daily at **22:00 Europe/Berlin** via APScheduler.

## Structure

- `dart_rankings/app.py` - Flask application factory + routes
- `dart_rankings/data.py` - In-memory data cache + APScheduler daily refresh
- `dart_rankings/fetcher.py` - DartConnect rankings API fetch
- `dart_rankings/parser.py` - API payload to player models
- `dart_rankings/qualifiers.py` - Qualifier slot selection logic
- `dart_rankings/report.py` - Template helper functions
- `dart_rankings/templates/` - Jinja2 HTML templates (responsive)
- `main.py` - Entry point

## Deployment

The app runs as a systemd service behind Caddy.

### Systemd service

Service file: `/etc/systemd/system/dart-rankings.service`

```ini
[Unit]
Description=Dart Rankings (next.jqve.dev)
After=network.target

[Service]
Type=simple
User=jqve
Group=jqve
WorkingDirectory=/home/jqve/next.jqve.dev
Environment=PORT=8000
ExecStart=/home/jqve/next.jqve.dev/.venv/bin/gunicorn -w 1 --threads 4 -b 127.0.0.1:8000 main:app
Restart=on-failure
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=dart-rankings

[Install]
WantedBy=multi-user.target
```

### Caddy reverse proxy

In `/etc/caddy/Caddyfile`:

```caddyfile
next.jqve.dev {
    tls /etc/caddy/certs/jqve.dev.pem /etc/caddy/certs/jqve.dev-key.pem
    encode gzip

    reverse_proxy localhost:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }

    log {
        output file /var/log/caddy/next-jqve-dev.log
    }
}
```

### Common commands

```bash
# Check service status
sudo systemctl status dart-rankings

# View logs
sudo journalctl -u dart-rankings -f

# Restart (triggers fresh data fetch)
sudo systemctl restart dart-rankings

# Deploy code changes
cd /home/jqve/next.jqve.dev
.venv/bin/pip install -r requirements.txt
sudo systemctl restart dart-rankings
```

## Run locally (development)

```bash
cd /home/jqve/next.jqve.dev
.venv/bin/python main.py
# Serves on http://localhost:8000
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Server port (dev mode only) |
| `FLASK_DEBUG` | *(unset)* | Set to `1` for debug mode |
| `MAIN_URL` | pdc-next-gen-2026 | Main rankings API URL |
| `YOUTH_URL` | pdc-next-gen-youth-2026 | Youth rankings API URL |
| `MAIN_QUAL` | `16` | Number of main qualifiers |
| `YOUTH_QUAL` | `4` | Number of youth qualifiers |
| `DARTCONNECT_COOKIE` | *(empty)* | Optional auth cookie |
