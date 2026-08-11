"""
Intake & Triage Agent

Parses emergency caller text/transcripts, calculates severity scores (1-5),
and categorizes incident types (Medical, Fire, Crime, Hazmat).
"""
class TriageAgent:
    """Specialized Gemini agent for emergency triage and severity assessment."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    async def evaluate_description(self, raw_description: str) -> dict:
        """Evaluates raw caller text to extract severity and category."""
        return {
            "severity": 1,
            "category": "pending_triage",
            "extracted_keywords": []
        }
