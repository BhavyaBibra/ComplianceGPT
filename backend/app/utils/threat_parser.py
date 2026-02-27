import re
from typing import Dict, Any

def parse_threat_intent(question: str) -> Dict[str, Any]:
    """
    Detects MITRE ATT&CK techniques or broad threat keywords in the user question.
    Returns structured threat intent.
    """
    threat_intent = False
    technique_id = None
    threat_keyword = None

    # MITRE ATT&CK Technique ID pattern (e.g., T1059, T1059.001)
    technique_pattern = r'\b(T\d{4}(?:\.\d{3})?)\b'

    # Common threat keywords
    threat_keywords = [
        "phishing", "ransomware", "credential dumping", "malware", 
        "brute force", "exfiltration", "persistence", "privilege escalation",
        "lateral movement", "mitigate", "mitigation", "attack", "threat"
    ]
    
    question_lower = question.lower()

    if match := re.search(technique_pattern, question, re.IGNORECASE):
        technique_id = match.group(1).upper()
        threat_intent = True
    else:
        for kw in threat_keywords:
            if kw in question_lower:
                threat_keyword = kw
                threat_intent = True
                break

    return {
        "threat_intent": threat_intent,
        "technique_id": technique_id,
        "threat_keyword": threat_keyword
    }
