# src/person_b/explain_api.py
import os
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


def explain_risk(applicant: dict, risk_score: float, cohort_rate: float) -> str:
    """Call Gemini to produce a 1-2 sentence plain-language risk explanation, or use heuristic fallback."""
    client = _get_client()
    if client:
        prompt = (
            "You are a loan underwriting analyst. Given the applicant data below, "
            "write exactly 1-2 sentences explaining why this applicant presents "
            "the indicated level of default risk. Be specific about which factors "
            "drive the risk assessment. Do not use bullet points or headers.\n\n"
            f"Applicant data:\n"
            f"  Monthly income: ${applicant.get('income', 0):,}\n"
            f"  Debt ratio: {applicant.get('debt_ratio', 0):.0%}\n"
            f"  Open credit lines: {applicant.get('credit_lines', 0)}\n"
            f"  Past delinquencies (90+ days): {applicant.get('delinquencies', 0)}\n"
            f"  Number of dependents: {applicant.get('dependents', 0)}\n\n"
            f"ML-predicted default risk score: {risk_score:.2f} (0 = no risk, 1 = certain default)\n"
            f"Cohort default rate: {cohort_rate:.1f}%\n"
        )
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"  [Gemini API call failed] {e}")

    # Deterministic fallback explanation
    income = applicant.get("income", 0)
    debt = applicant.get("debt_ratio", 0)
    delinq = applicant.get("delinquencies", 0)

    if risk_score <= 0.15 and delinq == 0 and debt <= 0.35:
        return (
            f"Applicant displays exceptionally low default risk ({risk_score:.1%}) with a solid monthly income of ${income:,}, "
            f"a conservative debt ratio of {debt:.0%}, and zero past delinquencies. "
            f"Historical cohort default rate is low at {cohort_rate:.1f}%."
        )
    elif risk_score >= 0.50 or delinq >= 2 or debt >= 0.50:
        return (
            f"Applicant presents elevated default risk ({risk_score:.1%}) driven by a high debt ratio ({debt:.0%}) "
            f"and {delinq} reported past delinquencies. "
            f"Their peer cohort reflects an increased default probability of {cohort_rate:.1f}%."
        )
    else:
        return (
            f"Applicant exhibits moderate credit risk ({risk_score:.1%}) with sustainable income (${income:,}) "
            f"balanced against a {debt:.0%} debt ratio and {delinq} delinquencies. "
            f"Similar peer cohort default rate is {cohort_rate:.1f}%."
        )


# --------------- test driver ---------------
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    from person_b.fake_applicants import fake_applicants

    # Made-up risk_score and cohort_rate values matched to risk labels
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
        print(f"\n--- Applicant {i+1} ({label} risk) ---")
        print(f"  Income=${applicant['income']:,}  Debt={applicant['debt_ratio']:.0%}  "
              f"Delinq={applicant['delinquencies']}  Score={score}")
        explanation = explain_risk(applicant, score, cohort)
        print(f"  Explanation: {explanation}")
        # Small delay to respect free-tier rate limits
        time.sleep(4)
