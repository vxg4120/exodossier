"""Minimal DB connection helpers. No ORM, no pooling.

Ported from the satellite platform's common/db.py — same shape, different default database
(`exo` instead of `oei`). The exo database is a separate database on the SAME TimescaleDB
container (host port 5433); Wave 1 never touches the oei database.
"""

import os

import psycopg

DEFAULT_DATABASE_URL = "postgresql://oei:oei@localhost:5433/exo"


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_conn() -> psycopg.Connection:
    """Return a psycopg connection to DATABASE_URL, autocommit off (the default)."""
    return psycopg.connect(_database_url())


def get_autocommit_conn() -> psycopg.Connection:
    """Return a psycopg connection with autocommit on, for DDL/migrations."""
    return psycopg.connect(_database_url(), autocommit=True)
