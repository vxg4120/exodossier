"""Request-scoped, read-only database dependency.

Ported in shape from the satellite platform's ``api/deps.py``. Yields a psycopg connection from
the shared ``common.db.get_conn`` helper, configured for this API's needs: rows as dicts (routers
read columns by name) and the transaction marked READ ONLY so the read-only contract is enforced
by Postgres itself, not merely by convention. A Wave-2 light-curve run writes to other tables on
the same database concurrently; this connection can never touch them.
"""

from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row

from common.db import get_conn


def get_db() -> Iterator[psycopg.Connection]:
    conn = get_conn()
    try:
        conn.row_factory = dict_row
        # Applied to the transaction the first SELECT opens; belt-and-suspenders against writes.
        conn.read_only = True
        yield conn
    finally:
        conn.close()
