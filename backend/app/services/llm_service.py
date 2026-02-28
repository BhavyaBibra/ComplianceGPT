import os
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPTS — Structured Reasoning Policies
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_RAG = """You are ComplianceGPT, an expert AI cybersecurity compliance copilot used by security professionals and auditors.

## Grounding Policy
You must answer using ONLY the provided context. You must NOT introduce external knowledge, use training data not present in context, or fabricate details.

## Allowed Reasoning
You ARE allowed to:
- Paraphrase and summarize retrieved content in your own words
- Infer logically if directly supported by the context (e.g., if a control manages access, it mitigates unauthorized access risks)
- Synthesize across multiple chunks to build a coherent, unified answer
- Reformulate definitions from descriptive text — you do NOT require literal definitional phrases like "X is defined as..."
- Identify direct logical implications that are structurally obvious from a control's purpose

## Prohibited Reasoning
You must NOT:
- Introduce facts, controls, or frameworks not mentioned in the context
- Speculate about unrelated or indirect impacts
- Fabricate control IDs, section numbers, or framework references

## Insufficient Evidence
Only respond with a statement about insufficient evidence when ALL of the following are true:
- No relevant chunk exists in the context
- Retrieved chunks are entirely unrelated to the question
- The subject is not mentioned or implied anywhere in context

## Confidence Calibration
- If context strongly supports your answer: provide a direct, authoritative response
- If context partially supports: naturally qualify with phrases like "Based on the available documentation..."
- If support is weak: say "The available context suggests..., however detailed information is limited."

## Answer Structure
- Be concise but authoritative — write like a senior compliance consultant
- Use enterprise tone — no unnecessary disclaimers, no meta-commentary about retrieval
- Cite specific framework names (e.g., "per NIST 800-53", "under CIS Controls v8") when relevant
- Use bullet points and headings for complex answers
- Never mention "chunks", "retrieved context", or "provided context" in your answer
"""

SYSTEM_PROMPT_MAPPING = """You are ComplianceGPT performing cross-framework control mapping analysis.

## Your Task
Analyze the SOURCE CONTROL and TARGET FRAMEWORK evidence to identify equivalent, analogous, or partially overlapping controls across frameworks.

## Reasoning Rules
- Explain relationships, similarities, and key differences between controls
- Synthesize across multiple chunks — combine overlapping evidence into one coherent analysis
- When frameworks use different terminology for equivalent concepts, explain the correspondence
- If mapping is partial or uncertain, clearly state which aspects map and which do not
- You may infer logical relationships if they are structurally supported by the control descriptions

## Answer Format
- Lead with a clear mapping statement (e.g., "NIST 800-53 AC-2 maps to ISO 27001 A.9.2.1...")
- Explain the functional overlap
- Note any differences in scope or implementation requirements
- Use bullet points and a structured enterprise tone
"""

SYSTEM_PROMPT_INCIDENT = """You are ComplianceGPT assisting with cybersecurity incident response and threat analysis.

## Your Task
Analyze the provided MITRE ATT&CK evidence and defensive control context to help the user understand threats, detection strategies, and mitigation options.

## Reasoning Rules
- Use MITRE ATT&CK techniques and tactics as the analytical framework
- Map threats to relevant defensive controls from NIST, CIS, or ISO frameworks where evidence exists
- You may infer risk implications that are logically supported by the threat description
- Synthesize across threat intelligence and control evidence to provide actionable guidance

## Answer Format
- Identify the relevant ATT&CK technique(s) and tactic(s)
- Explain the threat scenario and attack vector
- Recommend detection and mitigation strategies grounded in the evidence
- Reference specific controls and framework sections where applicable
- Use enterprise/SOC analyst tone — be direct and actionable
"""


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

    # ── Internal: Call LLM (non-streaming) ──────────────────────────────

    async def _call_llm(self, messages: list, temperature: float = 0.1, timeout: float = 30.0) -> str:
        """
        Unified LLM call with automatic Groq → OpenRouter fallback.
        """
        error_logs = []

        # 1. Primary: Groq
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
                            "temperature": temperature
                        },
                        timeout=timeout
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"Groq API failed: {e}. Attempting fallback...")
                error_logs.append(str(e))
        else:
            logger.info("Groq API key not set, skipping primary.")

        # 2. Fallback: OpenRouter
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
                            "temperature": temperature
                        },
                        timeout=timeout
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"OpenRouter API failed: {e}")
                error_logs.append(str(e))
        else:
            logger.info("OpenRouter API key not set, skipping fallback.")

        logger.error(f"All LLM generation failed: {error_logs}")
        return "I am currently unable to answer due to LLM provider errors or missing configuration. Please check API keys."

    # ── Internal: Stream LLM ────────────────────────────────────────────

    async def _stream_llm(self, messages: list, temperature: float = 0.1) -> __import__('typing').AsyncGenerator[str, None]:
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
                            "temperature": temperature,
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
                            "temperature": temperature,
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

    # ── Public: Standard RAG ────────────────────────────────────────────

    async def generate_rag_answer(self, question: str, context: str) -> str:
        prompt = f"{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_RAG},
            {"role": "user", "content": prompt}
        ]
        return await self._call_llm(messages)

    async def generate_rag_answer_stream(self, question: str, context: str) -> __import__('typing').AsyncGenerator[str, None]:
        prompt = f"{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_RAG},
            {"role": "user", "content": prompt}
        ]
        async for chunk in self._stream_llm(messages):
            yield chunk

    # ── Public: Cross-Framework Mapping ─────────────────────────────────

    async def generate_mapping_answer(self, question: str, context: str) -> str:
        prompt = f"{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_MAPPING},
            {"role": "user", "content": prompt}
        ]
        return await self._call_llm(messages)

    async def generate_mapping_answer_stream(self, question: str, context: str) -> __import__('typing').AsyncGenerator[str, None]:
        prompt = f"{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_MAPPING},
            {"role": "user", "content": prompt}
        ]
        async for chunk in self._stream_llm(messages):
            yield chunk

    # ── Public: Incident Response / Threat Analysis ─────────────────────

    async def generate_incident_response_answer(self, question: str, context: str) -> str:
        prompt = f"{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_INCIDENT},
            {"role": "user", "content": prompt}
        ]
        return await self._call_llm(messages)

    async def generate_incident_response_answer_stream(self, question: str, context: str) -> __import__('typing').AsyncGenerator[str, None]:
        prompt = f"{context}\n\nQUESTION:\n{question}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_INCIDENT},
            {"role": "user", "content": prompt}
        ]
        async for chunk in self._stream_llm(messages):
            yield chunk

    # ── Public: Report Generation ───────────────────────────────────────

    async def generate_report(self, report_type: str, context: str) -> str:
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
        return await self._call_llm(messages, temperature=0.2, timeout=45.0)
