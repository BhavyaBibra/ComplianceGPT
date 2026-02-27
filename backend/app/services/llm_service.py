import os
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """
    Service responsible for interacting with the Groq API (and OpenRouter fallback).
    Manages prompt construction, LLM generation, and fallback logic.
    """
    
    def __init__(self):
        self.groq_api_key = settings.groq_api_key
        self.openrouter_api_key = settings.openrouter_api_key
        
        # Primary: Groq uses OpenAI-compatible endpoint
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        
        self.system_prompt = (
            "You are ComplianceGPT, an AI cybersecurity compliance copilot. "
            "Answer ONLY using provided context. Cite frameworks explicitly. "
            "If answer not in context, say insufficient evidence."
        )
        
    async def generate_rag_answer(self, question: str, context: str) -> str:
        """
        Generate an answer using Groq. Uses OpenRouter if Groq fails.
        """
        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        error_logs = []
        
        # 1. Attempt using Groq primary
        if self.groq_api_key:
            try:
                logger.info("Calling Groq LLM API...")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.groq_url,
                        headers={"Authorization": f"Bearer {self.groq_api_key}"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": messages,
                            "temperature": 0.0
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"Groq API failed: {e}. Attempting fallback...")
                error_logs.append(str(e))
        else:
            logger.info("Groq API key not set, skipping primary.")

        # 2. Attempt using OpenRouter fallback
        if self.openrouter_api_key:
            try:
                logger.info("Calling OpenRouter LLM API fallback...")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.openrouter_url,
                        headers={
                            "Authorization": f"Bearer {self.openrouter_api_key}",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "ComplianceGPT"
                        },
                        json={
                            "model": "meta-llama/llama-3.3-70b-instruct",
                            "messages": messages,
                            "temperature": 0.0
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"OpenRouter API failed: {e}")
                error_logs.append(str(e))
        else:
            logger.info("OpenRouter API key not set, skipping fallback.")
            
        logger.error(f"All LLM generation failed or no keys configured: {error_logs}")
        return "I am currently unable to answer due to LLM provider errors or missing configuration. Please check API keys."

    async def _stream_llm(self, messages: list) -> __import__('typing').AsyncGenerator[str, None]:
        import json
        
        # Primary: Groq
        if self.groq_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        self.groq_url,
                        headers={"Authorization": f"Bearer {self.groq_api_key}"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": messages,
                            "temperature": 0.0,
                            "stream": True
                        },
                        timeout=30.0
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    return
                                try:
                                    chunk_data = json.loads(data_str)
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
                return
            except Exception as e:
                logger.warning(f"Groq API streaming failed: {e}. Attempting fallback...")

        # Fallback: OpenRouter
        if self.openrouter_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        self.openrouter_url,
                        headers={
                            "Authorization": f"Bearer {self.openrouter_api_key}",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "ComplianceGPT"
                        },
                        json={
                            "model": "meta-llama/llama-3.3-70b-instruct",
                            "messages": messages,
                            "temperature": 0.0,
                            "stream": True
                        },
                        timeout=30.0
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    return
                                try:
                                    chunk_data = json.loads(data_str)
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
                return
            except Exception as e:
                logger.error(f"OpenRouter API streaming failed: {e}")
        
        yield "I am currently unable to answer due to LLM provider errors or missing configuration. Please check API keys."

    async def generate_rag_answer_stream(self, question: str, context: str) -> __import__('typing').AsyncGenerator[str, None]:
        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        async for chunk in self._stream_llm(messages):
            yield chunk

    async def generate_mapping_answer(self, question: str, context: str) -> str:
        """
        Specialized LLM generation for cross-framework control mapping.
        """
        mapping_system_prompt = (
            "You are ComplianceGPT performing cross-framework control mapping. "
            "Use evidence to explain relationships, similarities, and differences. "
            "If mapping uncertain, state partial mapping."
        )
        
        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": mapping_system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Primary provider
        if self.groq_api_key:
            try:
                # Re-using the direct httpx call logic as _call_openrouter_format is not defined
                logger.info("Calling Groq LLM API for mapping...")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.groq_url,
                        headers={"Authorization": f"Bearer {self.groq_api_key}"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": messages,
                            "temperature": 0.0
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Groq API error during mapping: {e}")
                
        # Fallback provider
        if self.openrouter_api_key:
            try:
                # Re-using the direct httpx call logic as _call_openrouter_format is not defined
                logger.info("Calling OpenRouter LLM API fallback for mapping...")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.openrouter_url,
                        headers={
                            "Authorization": f"Bearer {self.openrouter_api_key}",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "ComplianceGPT"
                        },
                        json={
                            "model": "meta-llama/llama-3.3-70b-instruct",
                            "messages": messages,
                            "temperature": 0.0
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"OpenRouter API error during mapping fallback: {e}")
                
        return "I am currently unable to map these controls due to LLM provider errors."

    async def generate_mapping_answer_stream(self, question: str, context: str) -> __import__('typing').AsyncGenerator[str, None]:
        mapping_system_prompt = (
            "You are ComplianceGPT performing cross-framework control mapping. "
            "Use evidence to explain relationships, similarities, and differences. "
            "If mapping uncertain, state partial mapping."
        )
        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": mapping_system_prompt},
            {"role": "user", "content": prompt}
        ]
        async for chunk in self._stream_llm(messages):
            yield chunk

    async def generate_incident_response_answer(self, question: str, context: str) -> str:
        """
        Specialized LLM generation for cybersecurity incident response and MITRE mitigation.
        """
        ir_system_prompt = (
            "You are ComplianceGPT assisting with cybersecurity incident response. "
            "Use MITRE evidence and defensive controls to explain threat, detection, and mitigation."
        )
        
        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": ir_system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Primary provider
        if self.groq_api_key:
            try:
                logger.info("Calling Groq LLM API for incident response...")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.groq_url,
                        headers={"Authorization": f"Bearer {self.groq_api_key}"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": messages,
                            "temperature": 0.0
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Groq API error during IR: {e}")
                
        # Fallback provider
        if self.openrouter_api_key:
            try:
                logger.info("Calling OpenRouter LLM API fallback for incident response...")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.openrouter_url,
                        headers={
                            "Authorization": f"Bearer {self.openrouter_api_key}",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "ComplianceGPT"
                        },
                        json={
                            "model": "meta-llama/llama-3.3-70b-instruct",
                            "messages": messages,
                            "temperature": 0.0
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"OpenRouter API error during IR fallback: {e}")
                
        return "I am currently unable to process incident response due to LLM provider errors."

    async def generate_incident_response_answer_stream(self, question: str, context: str) -> __import__('typing').AsyncGenerator[str, None]:
        ir_system_prompt = (
            "You are ComplianceGPT assisting with cybersecurity incident response. "
            "Use MITRE evidence and defensive controls to explain threat, detection, and mitigation."
        )
        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": ir_system_prompt},
            {"role": "user", "content": prompt}
        ]
        async for chunk in self._stream_llm(messages):
            yield chunk

    async def generate_report(self, report_type: str, context: str) -> str:
        """
        Specialized LLM generation for synthesizing conversation history into a structured markdown report.
        """
        if report_type == "mapping":
            focus = "cross-framework control mapping relationships, highlighting similarities, differences, and gaps"
        elif report_type == "incident":
            focus = "threat intelligence and defensive control mitigation strategies based on MITRE ATT&CK"
        else:
            focus = "a general executive summary of the compliance discussion"
            
        report_system_prompt = (
            f"You are ComplianceGPT generating a structured, professional cybersecurity compliance report. "
            f"Your primary focus is on {focus}. "
            "Produce clear sections, professional headings, bullet points, and explicitly reference the evidence and frameworks provided below. "
            "Output valid Markdown only."
        )
        
        prompt = f"CONVERSATION CONTEXT & EVIDENCE:\n{context}\n\nPlease generate the comprehensive markdown report based on the above."
        messages = [
            {"role": "system", "content": report_system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Reports should allow maximum output tokens
        # Primary provider
        if self.groq_api_key:
            try:
                logger.info("Calling Groq LLM API for report generation...")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.groq_url,
                        headers={"Authorization": f"Bearer {self.groq_api_key}"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": messages,
                            "temperature": 0.2
                        },
                        timeout=45.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Groq API error during report generation: {e}")
                
        # Fallback provider
        if self.openrouter_api_key:
            try:
                logger.info("Calling OpenRouter LLM API fallback for report generation...")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.openrouter_url,
                        headers={
                            "Authorization": f"Bearer {self.openrouter_api_key}",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "ComplianceGPT"
                        },
                        json={
                            "model": "meta-llama/llama-3.3-70b-instruct",
                            "messages": messages,
                            "temperature": 0.2
                        },
                        timeout=45.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"OpenRouter API error during report generation fallback: {e}")
                
        return "# Error\n\nI am currently unable to generate the report due to LLM provider downtime or missing API keys."
