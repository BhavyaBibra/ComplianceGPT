from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """
    Simple health check route to verify the API is running.
    """
    return {"status": "ok", "service": "ComplianceGPT Backend"}
