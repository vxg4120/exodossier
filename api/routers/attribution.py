"""GET /api/attribution -- the citations for every source the site serves (the NASA Exoplanet
Archive, ExoFOP, TESS, MAST, and the satellite catalogs behind Follow-up) and the honest framing."""

from fastapi import APIRouter

from api.queries import attribution

router = APIRouter(tags=["attribution"])


@router.get("/attribution")
def get_attribution():
    return attribution()
