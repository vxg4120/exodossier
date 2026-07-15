"""GET /api/target/{ident} -- the money endpoint.

Canonical identity + full crosswalk (every id/source) + every source_assertion grouped by
attribute (the who-says-what table) + per-attribute conflict flags + the resolved/canonical value
where the graph has one. ``ident`` is a candidate_id or any identifier (TOI/CTOI/KOI/name/TIC/host).
"""

from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_db
from api.queries import resolve_target

router = APIRouter(tags=["target"])


@router.get("/target/{ident}")
def get_target(ident: str, db: Annotated[psycopg.Connection, Depends(get_db)]):
    target = resolve_target(db, ident)
    if target is None:
        raise HTTPException(status_code=404, detail=f"No target resolves for {ident!r}")
    return target
