import logging
import time
from typing import List
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class ReportService:
    """
    Orchestrates building conversation context into structured reports.
    """
    def __init__(self):
        self.llm_service = LLMService()
        
    def _build_conversation_context(self, messages: List) -> str:
        """
        Condenses a list of ChatMessage payload dictionaries into a cohesive string.
        Extracts user questions, assistant answers, and evidence traces.
        """
        context_parts = []
        for i, msg in enumerate(messages):
            role = msg.role.upper()
            content = msg.content
            
            part = f"[{role} MESSAGE]\n{content}"
            
            # Surface citations/frameworks used for provenance
            meta = []
            if msg.citations:
                meta.append(f"Citations: {', '.join(msg.citations)}")
            if msg.frameworks_used:
                meta.append(f"Frameworks: {', '.join(msg.frameworks_used)}")
                
            if meta:
                part += f"\n(Metadata: {' | '.join(meta)})"
                
            context_parts.append(part)
            
        return "\n\n---\n\n".join(context_parts)

    async def generate_report(self, report_type: str, messages: List) -> str:
        """
        Builds the context string from messages and commands the LLM to synthesize it.
        """
        start_time = time.time()
        logger.info(f"Report Service: Formatting conversation history for {report_type} report.")
        
        context_str = self._build_conversation_context(messages)
        logger.info(f"Report Service: Context built ({len(context_str)} chars). Calling LLM...")
        
        markdown_content = await self.llm_service.generate_report(report_type, context_str)
        
        latency = time.time() - start_time
        logger.info(f"Report Service: Successfully generated {report_type} report in {latency:.2f}s.")
        
        return markdown_content
