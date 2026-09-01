# src/person_b/decision_engine.py
import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=5,
                    initial_delay=2.0,
                    max_delay=15.0,
                    http_status_codes=[429, 500, 502, 503, 504]
                )
            )
        )
    except Exception as e:
        print(f"  [Gemini client init warning] {e}")
        return None

MODEL = "gemini-2.5-flash-lite"

VALID_DECISIONS = {"Approve", "Manual Review", "Decline"}
VALID_CONFIDENCES = {"High", "Medium", "Low"}


def _fallback_from_explanation(explanation: str) -> dict:
    """Keyword-based heuristic when Gemini is unavailable."""
    text = explanation.lower()
    if any(w in text for w in ["extremely high", "very high", "unsustainable", "severe"]):
        return {"recommendation": "Decline", "confidence": "High"}
    if any(w in text for w in ["high risk", "high default"]):
        return {"recommendation": "Decline", "confidence": "Medium"}
    if any(w in text for w in ["moderate", "elevated", "borderline"]):
        return {"recommendation": "Manual Review", "confidence": "Medium"}
    if any(w in text for w in ["very low", "excellent", "exceptionally"]):
        return {"recommendation": "Approve", "confidence": "High"}
    if any(w in text for w in ["low risk", "low default"]):
        return {"recommendation": "Approve", "confidence": "Medium"}
    return {"recommendation": "Manual Review", "confidence": "Low"}


def recommend_decision(explanation: str) -> dict:
    """Call Gemini to produce a structured underwriting decision from a risk explanation.

    Returns: {"recommendation": "Approve"|"Manual Review"|"Decline",
              "confidence": "High"|"Medium"|"Low"}
    """
    client = _get_client()
    if client:
        prompt = (
            "You are a senior loan underwriter. Based on the risk explanation below, "
            "output a JSON object with exactly two keys:\n"
            '  "recommendation": one of "Approve", "Manual Review", or "Decline"\n'
            '  "confidence": one of "High", "Medium", or "Low"\n\n'
            "Return ONLY the raw JSON object, no markdown, no commentary.\n\n"
            f"Risk explanation:\n{explanation}"
        )
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            if response and response.text:
                raw = response.text.strip()
                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                result = json.loads(raw)
                # Validate fields
                if result.get("recommendation") in VALID_DECISIONS and result.get("confidence") in VALID_CONFIDENCES:
                    return result
        except Exception as e:
            print(f"  [Gemini fallback] {e}")

    return _fallback_from_explanation(explanation)


# --------------- test driver ---------------
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    from person_b.fake_applicants import fake_applicants
    from person_b.explain_api import explain_risk

    test_params = [
        (0.05, 3.2),   # Low
        (0.08, 2.8),   # Low
        (0.32, 8.5),   # Medium
        (0.41, 11.0),  # Medium
        (0.28, 7.1),   # Medium
        (0.72, 18.4),  # High
        (0.68, 16.9),  # High
        (0.91, 24.5),  # High
    ]

    for i, (applicant, (score, cohort)) in enumerate(zip(fake_applicants, test_params)):
        label = applicant.get("risk_level_label", "?")
        print(f"\n=== Applicant {i+1} ({label} risk) ===")

        explanation = explain_risk(applicant, score, cohort)
        print(f"  Explanation: {explanation[:120]}...")

        decision = recommend_decision(explanation)
        print(f"  Decision:    {json.dumps(decision)}")
        time.sleep(4)
