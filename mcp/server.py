"""ExoDossier MCP server — the agent-native window on the exoplanet conflict graph.

A read-only Model Context Protocol server exposing the same identity-graph + conflict queries as
the HTTP API (it imports ``api.queries``, so the API, the web catalog and the agent tools can never
disagree). Verified novel: no exoplanet MCP server existed when this was built. It surfaces where
the archives disagree, with provenance — it does not adjudicate or confirm.

Tools (all read-only):
  * catalog_stats()                    -> graph totals + cross-source conflict counts
  * search_targets(query)              -> resolve TIC/TOI/CTOI/KOI/name/host to candidate targets
  * resolve_target(id)                 -> identity + full crosswalk + who-says-what + conflict flags
  * target_conflicts(id)               -> just the conflicting attributes for one target
  * list_conflicts(type, limit)        -> a page of the disposition|radius|teff conflict corpus

Run (stdio transport):  .venv/bin/python mcp/server.py
See mcp/README.md for client wiring and a sample agent query.

Note on the directory name: this file lives in a ``mcp/`` directory that is intentionally NOT a
Python package (no __init__.py), so it never shadows the installed ``mcp`` SDK. It appends the repo
root to ``sys.path`` to import the shared ``api``/``common`` modules.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

from collections.abc import Iterator  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from typing import Any  # noqa: E402

import psycopg  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from api import queries  # noqa: E402
from common.db import get_conn  # noqa: E402

mcp = FastMCP("exodossier")


@contextmanager
def _ro_db() -> Iterator[psycopg.Connection]:
    """A per-call read-only connection to the exo identity graph (never writes; never touches the
    Wave-2 light-curve tables)."""
    conn = get_conn()
    try:
        conn.row_factory = dict_row
        conn.read_only = True
        yield conn
    finally:
        conn.close()


@mcp.tool()
def catalog_stats() -> dict[str, Any]:
    """Graph totals (stars, candidates, crosswalk identifiers, source assertions) and the
    cross-source conflict counts (disposition, dramatic FALSE_POSITIVE-vs-CONFIRMED, radius, Teff),
    plus the ingestion ledger."""
    with _ro_db() as db:
        return queries.catalog_stats(db)


@mcp.tool()
def search_targets(query: str, limit: int = 25) -> dict[str, Any]:
    """Resolve any TIC / TOI / CTOI / KOI / planet name / host name to candidate targets. A host
    match expands to every candidate of that star. Returns ``{query, count, results}``."""
    with _ro_db() as db:
        results = queries.search_targets(db, query, limit)
    return {"query": query, "count": len(results), "results": results}


@mcp.tool()
def resolve_target(id: str) -> dict[str, Any]:
    """The full target dossier for one candidate: canonical identity, the complete
    TIC/TOI/CTOI/KOI/Gaia crosswalk, every source assertion grouped by attribute (the who-says-what
    table), which attributes disagree across sources, and the resolved/canonical value where the
    graph has one. ``id`` is a candidate_id or any identifier (TOI/CTOI/KOI/name/TIC/host)."""
    with _ro_db() as db:
        target = queries.resolve_target(db, id)
    if target is None:
        return {"error": "not_found", "message": f"No target resolves for {id!r}"}
    return target


@mcp.tool()
def target_conflicts(id: str) -> dict[str, Any]:
    """Answer 'does anyone disagree about this target?' — just the conflicting attributes for one
    target, each with the per-source claims. ``id`` is a candidate_id or any identifier."""
    with _ro_db() as db:
        result = queries.target_conflicts(db, id)
    if result is None:
        return {"error": "not_found", "message": f"No target resolves for {id!r}"}
    return result


@mcp.tool()
def list_conflicts(type: str = "disposition", limit: int = 25, offset: int = 0) -> dict[str, Any]:
    """A page of the browsable conflict corpus. ``type`` is one of disposition | radius | teff.
    Each row deep-links to a target via its candidate_id. Returns
    ``{type, rows, total, limit, offset}``."""
    if type not in queries.CONFLICT_TYPES:
        return {
            "error": "bad_type",
            "message": f"unknown conflict type {type!r}",
            "valid_types": list(queries.CONFLICT_TYPES),
        }
    with _ro_db() as db:
        return queries.list_conflicts(db, type, limit, offset)


if __name__ == "__main__":
    mcp.run()
