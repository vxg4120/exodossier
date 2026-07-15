"""GET /api/stats -- graph totals, cross-source conflict counts, and the ingestion ledger."""

from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_db
from api.queries import catalog_stats

router = APIRouter(tags=["stats"])


@router.get("/stats")
def get_stats(db: Annotated[psycopg.Connection, Depends(get_db)]):
    return catalog_stats(db)
