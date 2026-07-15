"""GET /api/attribution -- NASA Exoplanet Archive + ExoFOP + TESS citations and honest framing."""

from fastapi import APIRouter

from api.queries import attribution

router = APIRouter(tags=["attribution"])


@router.get("/attribution")
def get_attribution():
    return attribution()
