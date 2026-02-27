from typing import List, Dict, Any

def format_compliance_citation(source_id: str, snippet: str) -> str:
    """
    Placeholder helper function to nicely format a compliance framework citation.
    """
    return f"[{source_id}]: {snippet[:50]}..."

def extract_citations(retrieval_results: List[Dict[str, Any]]) -> List[str]:
    """
    Extracts a unique list of frameworks used in the retrieved context.
    Provides these frameworks so the UI can highlight which ones helped construct the answer.
    """
    frameworks = set()
    for result in retrieval_results:
        fw = result.get("framework")
        if fw:
            frameworks.add(fw)
            
    return sorted(list(frameworks))
