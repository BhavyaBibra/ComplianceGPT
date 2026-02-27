from pydantic import BaseModel
from typing import List, Dict, Any

class QueryRequest(BaseModel):
    """
    Pydantic model for incoming RAG search queries.
    """
    question: str
    frameworks: List[str] | None = None
    stream: bool = False

class QueryResponse(BaseModel):
    """
    Pydantic model for outgoing LLM responses.
    """
    answer: str
    mapping_mode: bool = False
    incident_mode: bool = False
    citations: List[str] = []
    frameworks_used: List[str] = []
    retrieved_chunks: List[Dict[str, Any]] = []

class ReportMessage(BaseModel):
    role: str
    content: str
    citations: List[str] | None = None
    frameworks_used: List[str] | None = None

class ReportRequest(BaseModel):
    """
    Request model for generating a structured compliance report.
    """
    report_type: str  # "mapping", "incident", "summary"
    messages: List[ReportMessage]

class ReportResponse(BaseModel):
    """
    Response model containing the generated markdown report.
    """
    markdown: str
