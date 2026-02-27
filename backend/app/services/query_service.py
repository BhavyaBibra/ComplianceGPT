import logging
from typing import Dict, Any, List
import time
from app.services.retrieval_service import RetrievalService, build_context
from app.services.llm_service import LLMService
from app.services.threat_service import ThreatService
from app.utils.formatters import extract_citations
from app.utils.control_parser import parse_control_intent
from app.utils.threat_parser import parse_threat_intent

logger = logging.getLogger(__name__)

class QueryService:
    """
    Orchestrates RAG pipelines integrating chunk retrieval, mapping logics, threat intelligence, and LLM synthesis.
    """
    
    def __init__(self):
        self.retrieval_service = RetrievalService()
        self.llm_service = LLMService()
        self.threat_service = ThreatService(self.retrieval_service)
        
    async def process_query(self, question: str, frameworks: List[str] | None = None) -> Dict[str, Any]:
        """
        Runs full RAG pipeline returning answer, citations, frameworks_used, and chunks.
        """
        start_time = time.time()
        logger.info(f"Query Service: Starting process for question: {question} with frameworks: {frameworks}")
        
        # 0. Check for Control Mapping Intent
        mapping_intent = parse_control_intent(question)
        
        if mapping_intent["mapping_intent"] and mapping_intent["control_id"]:
            logger.info(f"Query Service: Detected MAPPING INTENT for control {mapping_intent['control_id']} from {mapping_intent['source_framework']}")
            return await self._process_mapping_query(question, mapping_intent, frameworks, start_time)
            
        # 0.5 Check for Threat / Incident Intent
        threat_intent = parse_threat_intent(question)
        if threat_intent["threat_intent"]:
            logger.info(f"Query Service: Detected THREAT INTENT (Tech: {threat_intent['technique_id']}, Keyword: {threat_intent['threat_keyword']})")
            return await self._process_threat_query(question, threat_intent, frameworks, start_time)
        
        # 1. Retrieve chunks (Standard RAG)
        retrieval_results = await self.retrieval_service.get_relevant_chunks(question, frameworks=frameworks, limit=5)
        
        # Log distribution
        distribution = {}
        for r in retrieval_results:
            fw = r.get("framework", "Unknown")
            distribution[fw] = distribution.get(fw, 0) + 1
        logger.info(f"Query Service: Retrieved {len(retrieval_results)} chunks. Distribution: {distribution}")
        
        # 2. Build context and citations
        context = build_context(retrieval_results)
        citations = extract_citations(retrieval_results)
        
        # 3. Call LLM
        logger.info("Query Service: Generating RAG answer...")
        answer = await self.llm_service.generate_rag_answer(question, context)
        
        latency = time.time() - start_time
        logger.info(f"Query Service: Process complete in {latency:.2f}s.")
        
        return {
            "answer": answer,
            "citations": citations,
            "frameworks_used": citations,
            "retrieved_chunks": retrieval_results
        }

    async def process_query_stream(self, question: str, frameworks: List[str] | None = None) -> __import__('typing').AsyncGenerator[str, None]:
        import json
        
        start_time = time.time()
        logger.info(f"Query Service: Starting STREAM process for question: {question}")
        
        mapping_intent = parse_control_intent(question)
        if mapping_intent["mapping_intent"] and mapping_intent["control_id"]:
            async for chunk in self._process_mapping_query_stream(question, mapping_intent, frameworks, start_time):
                yield chunk
            return
            
        threat_intent = parse_threat_intent(question)
        if threat_intent["threat_intent"]:
            async for chunk in self._process_threat_query_stream(question, threat_intent, frameworks, start_time):
                yield chunk
            return
            
        retrieval_results = await self.retrieval_service.get_relevant_chunks(question, frameworks=frameworks, limit=5)
        context = build_context(retrieval_results)
        citations = extract_citations(retrieval_results)
        
        metadata = {
            "mapping_mode": False,
            "incident_mode": False,
            "citations": citations,
            "frameworks_used": citations,
            "retrieved_chunks": retrieval_results
        }
        yield f"data: {json.dumps({'type': 'metadata', 'data': metadata})}\n\n"
        
        logger.info("Query Service: Streaming RAG answer...")
        async for text_chunk in self.llm_service.generate_rag_answer_stream(question, context):
            yield f"data: {json.dumps({'type': 'content', 'text': text_chunk})}\n\n"
            
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    async def _process_mapping_query(self, question: str, intent: Dict[str, Any], frameworks: List[str] | None, start_time: float) -> Dict[str, Any]:
        """
        Specialized pipeline for cross-framework control mapping.
        """
        control_id = intent["control_id"]
        source_framework = intent["source_framework"]
        
        logger.info(f"Query Service: Executing Mapping Strategy for {control_id}")
        
        # 1. Retrieve chunks specifically concerning the source control ID
        source_chunks = await self.retrieval_service.get_relevant_chunks(
            query=control_id, 
            frameworks=[source_framework] if source_framework else None, 
            limit=3
        )
        
        # 2. Retrieve top chunks from target frameworks based on the semantic question
        target_chunks = await self.retrieval_service.get_relevant_chunks(
            query=question, 
            frameworks=frameworks, 
            limit=5
        )
        
        # 3. Build comparative context
        source_context = build_context(source_chunks)
        target_context = build_context(target_chunks)
        
        context = f"=== SOURCE CONTROL ===\n{source_context}\n\n=== TARGET FRAMEWORK EVIDENCE ===\n{target_context}"
        
        # Combine unique chunks for the frontend to render evidence
        all_chunks = source_chunks + target_chunks
        # De-duplicate evidence by chunk exact match
        seen = set()
        unique_chunks = []
        for c in all_chunks:
            if c["chunk"] not in seen:
                seen.add(c["chunk"])
                unique_chunks.append(c)
                
        citations = extract_citations(unique_chunks)
        
        logger.info("Query Service: Generating MAPPING answer...")
        answer = await self.llm_service.generate_mapping_answer(question, context)
        
        latency = time.time() - start_time
        logger.info(f"Query Service: Mapping Process complete in {latency:.2f}s.")
        
        return {
            "answer": answer,
            "citations": citations,
            "frameworks_used": citations,
            "retrieved_chunks": unique_chunks,
            "mapping_mode": True
        }

    async def _process_mapping_query_stream(self, question: str, intent: Dict[str, Any], frameworks: List[str] | None, start_time: float) -> __import__('typing').AsyncGenerator[str, None]:
        import json
        control_id = intent["control_id"]
        source_framework = intent["source_framework"]
        
        source_chunks = await self.retrieval_service.get_relevant_chunks(
            query=control_id, 
            frameworks=[source_framework] if source_framework else None, 
            limit=3
        )
        target_chunks = await self.retrieval_service.get_relevant_chunks(
            query=question, 
            frameworks=frameworks, 
            limit=5
        )
        
        source_context = build_context(source_chunks)
        target_context = build_context(target_chunks)
        context = f"=== SOURCE CONTROL ===\n{source_context}\n\n=== TARGET FRAMEWORK EVIDENCE ===\n{target_context}"
        
        all_chunks = source_chunks + target_chunks
        seen = set()
        unique_chunks = []
        for c in all_chunks:
            if c["chunk"] not in seen:
                seen.add(c["chunk"])
                unique_chunks.append(c)
                
        citations = extract_citations(unique_chunks)
        
        metadata = {
            "mapping_mode": True,
            "incident_mode": False,
            "citations": citations,
            "frameworks_used": citations,
            "retrieved_chunks": unique_chunks
        }
        yield f"data: {json.dumps({'type': 'metadata', 'data': metadata})}\n\n"
        
        async for text_chunk in self.llm_service.generate_mapping_answer_stream(question, context):
            yield f"data: {json.dumps({'type': 'content', 'text': text_chunk})}\n\n"
            
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    async def _process_threat_query(self, question: str, intent: Dict[str, Any], frameworks: List[str] | None, start_time: float) -> Dict[str, Any]:
        """
        Specialized pipeline for MITRE ATT&CK incident response and mitigation planning.
        """
        logger.info("Query Service: Executing Threat Mitigation Strategy")
        
        # Use ThreatService to build context and fetch corresponding chunks
        context, unique_chunks = await self.threat_service.build_threat_context(question, intent, frameworks)
        
        citations = extract_citations(unique_chunks)
        
        logger.info("Query Service: Generating INCIDENT RESPONSE answer...")
        answer = await self.llm_service.generate_incident_response_answer(question, context)
        
        latency = time.time() - start_time
        logger.info(f"Query Service: Threat Process complete in {latency:.2f}s.")
        
        return {
            "answer": answer,
            "citations": citations,
            "frameworks_used": citations,
            "retrieved_chunks": unique_chunks,
            "incident_mode": True
        }

    async def _process_threat_query_stream(self, question: str, intent: Dict[str, Any], frameworks: List[str] | None, start_time: float) -> __import__('typing').AsyncGenerator[str, None]:
        import json
        context, unique_chunks = await self.threat_service.build_threat_context(question, intent, frameworks)
        citations = extract_citations(unique_chunks)
        
        metadata = {
            "mapping_mode": False,
            "incident_mode": True,
            "citations": citations,
            "frameworks_used": citations,
            "retrieved_chunks": unique_chunks
        }
        yield f"data: {json.dumps({'type': 'metadata', 'data': metadata})}\n\n"
        
        async for text_chunk in self.llm_service.generate_incident_response_answer_stream(question, context):
            yield f"data: {json.dumps({'type': 'content', 'text': text_chunk})}\n\n"
            
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
