import logging
from typing import List, Dict, Any
from app.services.retrieval_service import RetrievalService, build_context

logger = logging.getLogger(__name__)

class ThreatService:
    """
    Orchestrates the retrieval and context building specialized for Incident Response 
    and MITRE ATT&CK mitigation reasoning.
    """
    def __init__(self, retrieval_service: RetrievalService):
        self.retrieval_service = retrieval_service
        
    async def build_threat_context(self, question: str, intent: Dict[str, Any], target_frameworks: List[str] | None) -> tuple[str, List[Dict[str, Any]]]:
        """
        Retrieves MITRE technique chunks and target framework control chunks,
        then builds a specialized context string for incident response mapping.
        """
        technique_id = intent.get("technique_id")
        threat_keyword = intent.get("threat_keyword")
        
        # Prefer the exact technique ID if found, otherwise use the keyword
        mitre_query = technique_id if technique_id else threat_keyword
        if not mitre_query:
            mitre_query = question
            
        logger.info(f"Threat Service: Retrieving MITRE intelligence for '{mitre_query}'")
        
        # 1. Retrieve MITRE chunks (specifically targeting 'mitre' framework)
        mitre_chunks = await self.retrieval_service.get_relevant_chunks(
            query=mitre_query,
            frameworks=["mitre"],
            limit=2
        )
        
        # 2. Retrieve defensive controls from user-selected target frameworks
        logger.info(f"Threat Service: Retrieving defensive controls for question.")
        control_chunks = await self.retrieval_service.get_relevant_chunks(
            query=question,
            frameworks=target_frameworks,
            limit=5
        )
        
        # 3. Build comparative/mitigation context
        mitre_context_str = build_context(mitre_chunks)
        control_context_str = build_context(control_chunks)
        
        context = f"=== MITRE TECHNIQUE ===\n{mitre_context_str}\n\n=== DEFENSIVE CONTROLS ===\n{control_context_str}"
        
        # Combine unique chunks for frontend evidence visualization
        all_chunks = mitre_chunks + control_chunks
        seen = set()
        unique_chunks = []
        for c in all_chunks:
            # deduplicate by exact chunk text
            if c["chunk"] not in seen:
                seen.add(c["chunk"])
                unique_chunks.append(c)
                
        return context, unique_chunks
