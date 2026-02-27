from fastapi import APIRouter, HTTPException
import logging
from app.models.schemas import ReportRequest, ReportResponse
from app.services.report_service import ReportService

router = APIRouter()
logger = logging.getLogger(__name__)

report_service = ReportService()

@router.post("/report", response_model=ReportResponse)
async def report_endpoint(request: ReportRequest):
    """
    Synthesizes a structured compliance report based on the provided conversation context.
    Supports "mapping", "incident", and "summary" report types.
    """
    try:
        logger.info(f"Received API query Request to generate {request.report_type} report.")
        
        # Ensure we have context to build
        if not request.messages:
            raise ValueError("No conversation messages provided to synthesize.")
            
        markdown_body = await report_service.generate_report(
            report_type=request.report_type,
            messages=request.messages
        )
        
        return ReportResponse(markdown=markdown_body)
    except ValueError as ve:
        logger.warning(f"Validation error generating report: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to generate report on /report endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error synthesizing report.")
