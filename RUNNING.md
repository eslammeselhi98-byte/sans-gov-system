Quick run instructions

Local (venv)

1. Copy `.env.example` to `.env` and edit values as needed.
2. Create venv and install dependencies:

```bash
make install
```

3. Run the backend:

```bash
make backend-run
```

Docker Compose (recommended for full stack)

1. Copy `.env.example` to `.env` and fill required secrets (especially `DB_PASSWORD` and `SECRET_KEY`).
2. Start services:

```bash
make compose-up
```

3. Tail logs:

```bash
make logs
```

Notes
- For local quick development you can set `DATABASE_URL=sqlite+aiosqlite:///./dev.db` in `backend/.env`.
- If Docker isn't available in your environment, run locally with `make install` + `make backend-run`.
- The backend will serve on port `${BACKEND_PORT:-8000}` inside the container or on `127.0.0.1:8001` when using the Makefile default.

Production service (systemd)

1. Copy the repo to the server, put it under `/var/www/sans-pms` (or your preferred path).
2. Create a system `.env` (outside version control) and set `SECRET_KEY`, DB credentials, etc.
3. Use the provided `docs/systemd/backend.service` as a template. Adjust `WorkingDirectory` and `EnvironmentFile` to your paths, then enable it:

```bash
sudo cp docs/systemd/backend.service /etc/systemd/system/sans-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now sans-backend.service
sudo journalctl -u sans-backend -f
```

Or run under `supervisord` using `docs/supervisor/backend.conf`.
