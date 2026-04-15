"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
