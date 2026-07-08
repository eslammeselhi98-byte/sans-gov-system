VENV=.venv
PY=${VENV}/bin/python
PIP=${VENV}/bin/pip

.PHONY: venv install backend-run backend-run-reload backend-migrate docker-up docker-build compose-up logs

venv:
	python3 -m venv ${VENV}
	${PY} -m pip install --upgrade pip setuptools wheel

install: venv
	${PIP} install -r backend/requirements.txt

backend-run:
	cd backend && case "${DATABASE_SYNC_URL:-${DATABASE_URL:-sqlite+aiosqlite:///./dev.db}}" in sqlite*) echo "Skipping alembic migrations for local SQLite dev database.";; *) ../${VENV}/bin/python -m alembic upgrade head;; esac && ../${VENV}/bin/python -m uvicorn main:app --host 127.0.0.1 --port ${BACKEND_PORT:-8001}

backend-run-reload:
	cd backend && case "${DATABASE_SYNC_URL:-${DATABASE_URL:-sqlite+aiosqlite:///./dev.db}}" in sqlite*) echo "Skipping alembic migrations for local SQLite dev database.";; *) ../${VENV}/bin/python -m alembic upgrade head;; esac && ../${VENV}/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port ${BACKEND_PORT:-8001}

backend-migrate:
	cd backend && case "${DATABASE_SYNC_URL:-${DATABASE_URL:-sqlite+aiosqlite:///./dev.db}}" in sqlite*) echo "Skipping migrations for local SQLite dev database";; *) ../${VENV}/bin/python -m alembic upgrade head;; esac

docker-build:
	docker compose build

docker-up:
	docker compose up --build

compose-up:
	docker compose up -d --build

logs:
	docker compose logs -f
