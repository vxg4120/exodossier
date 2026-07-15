.PHONY: venv migrate ingest build report test lint psql

venv:
	python3.14 -m venv .venv || python3.13 -m venv .venv || python3.12 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt

# Create the exo database on the existing oei-db container, then apply migrations (idempotent).
migrate:
	docker exec oei-db psql -U oei -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='exo'" \
		| grep -q 1 || docker exec oei-db psql -U oei -d postgres -c "CREATE DATABASE exo"
	.venv/bin/python scripts/migrate.py

# One polite pull of each catalog (24h freshness gate per endpoint; ledgered).
ingest:
	.venv/bin/python scripts/ingest_all.py

# Rebuild the identity graph (stars, candidates, crosswalk, assertions, resolution) from raw.
build:
	.venv/bin/python scripts/build_graph.py

# Write docs/reports/conflict_report.md.
report:
	.venv/bin/python quality/report.py

test:
	.venv/bin/python -m pytest

lint:
	.venv/bin/ruff check .

psql:
	docker exec -it oei-db psql -U oei -d exo
