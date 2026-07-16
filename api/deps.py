"""Request-scoped, read-only database dependencies.

Ported in shape from the satellite platform's ``api/deps.py``. Yields a psycopg connection from
the shared ``common.db.get_conn`` helper, configured for this API's needs: rows as dicts (routers
read columns by name) and the transaction marked READ ONLY so the read-only contract is enforced
by Postgres itself, not merely by convention. A Wave-2 light-curve run writes to other tables on
the same database concurrently; this connection can never touch them.

The Follow-up view (``api/routers/twoskies.py``) additionally reads a SECOND, foreign database:
the satellite identity graph ``oei`` (element sets + operator labels). ``get_oei_db`` opens that
connection strictly READ ONLY — ExoDossier never writes to ``oei`` and never migrates it.
"""

import os
from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row

from common.db import get_conn

# The Follow-up (Two Skies) bridge reads the satellite platform's ``oei`` database — a DIFFERENT
# database from ExoDossier's own ``exo`` — for satellite element sets and operator labels.
# Overridable via env, defaulting to the same local TimescaleDB cluster (host port 5433).
OEI_DATABASE_URL_DEFAULT = "postgresql://oei:oei@localhost:5433/oei"


def get_db() -> Iterator[psycopg.Connection]:
    conn = get_conn()
    try:
        conn.row_factory = dict_row
        # Applied to the transaction the first SELECT opens; belt-and-suspenders against writes.
        conn.read_only = True
        yield conn
    finally:
        conn.close()


def get_oei_db() -> Iterator[psycopg.Connection]:
    """Read-only connection to the satellite identity DB (``oei``) — the Follow-up bridge's second
    catalog. A distinct, foreign database from ExoDossier's own ``exo`` graph; this is its ONLY
    consumer here.

    READ ONLY is enforced at the transaction level, deliberately: the satellite platform may be
    ingesting fresh element sets into ``oei`` while this endpoint runs, so it must never write or
    migrate. Postgres MVCC lets these reads proceed against a consistent snapshot without blocking
    on that writer. The connection targets ``OEI_DATABASE_URL`` (falling back to the local default).
    """
    url = os.environ.get("OEI_DATABASE_URL", OEI_DATABASE_URL_DEFAULT)
    conn = psycopg.connect(url)
    try:
        conn.row_factory = dict_row
        conn.read_only = True
        yield conn
    finally:
        conn.close()
