import re
from typing import Dict, Any, Optional

def parse_control_intent(question: str) -> Dict[str, Any]:
    """
    Detects control identifiers in the user question and returns a structured mapping intent.
    Supports patterns like AC-2 (NIST 800-53), A.9.2 (ISO 27001), PR.AC (NIST CSF).
    """
    mapping_intent = False
    control_id = None
    source_framework = None

    # Matches AC-2, IA-5, etc.
    nist_800_53_pattern = r'\b([A-Z]{2}-\d+)\b'
    # Matches A.9.2, A.9.2.1, etc.
    iso_27001_pattern = r'\b(A\.\d+\.\d+(?:\.\d+)?)\b'
    # Matches PR.AC, ID.AM, etc.
    nist_csf_pattern = r'\b([A-Z]{2}\.[A-Z]{2}(?:-\d+)?)\b'

    # Mapping keywords
    mapping_keywords = ["map", "mapping", "equivalent", "compare", "versus", "vs", "relation"]
    
    question_lower = question.lower()
    
    if any(kw in question_lower for kw in mapping_keywords):
        mapping_intent = True

    if match := re.search(nist_800_53_pattern, question):
        control_id = match.group(1)
        source_framework = "nist80053"
        mapping_intent = True # If explicit control ID is found, assume strong intent for context
    elif match := re.search(iso_27001_pattern, question):
        control_id = match.group(1)
        source_framework = "iso27001"
        mapping_intent = True
    elif match := re.search(nist_csf_pattern, question):
        control_id = match.group(1)
        source_framework = "nistcsf"
        mapping_intent = True

    return {
        "control_id": control_id,
        "source_framework": source_framework,
        "mapping_intent": mapping_intent
    }
