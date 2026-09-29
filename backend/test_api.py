"""
End-to-end check for POST /api/analyze.

Prerequisites (run from the backend/ directory):
  1. python -m db.models
  2. python -m data_ingestion.seed_standards
  3. uvicorn main:app --reload      (leave running in another terminal)

Then:  python test_api.py

Exit code 0 = passed, 1 = failed.

Uses httpx, which is already pinned in requirements.txt (httpx<0.28).
"""
import json
import sys

import httpx

# Windows consoles default to cp1252, which cannot render characters such as the
# non-breaking hyphen (U+2011) that the LLM can return in its justification.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API_URL = "http://localhost:8000/api/analyze"
PAYLOAD = {"text": "Steel reinforcement bars, Fe500D grade, coastal construction"}

EXPECTED_IS = "IS 1786:2008"
EXPECTED_ALLIED_KEY = "test_methods"
EXPECTED_ALLIED_IS = "IS 1608:2005"
EXPECTED_CERT = "BIS ISI Mark"

# The first /api/analyze call lazily loads the BAAI/bge-m3 model, so allow plenty of time.
TIMEOUT_SECONDS = 300


def main() -> int:
    print("POST", API_URL)
    print("payload:", json.dumps(PAYLOAD))

    try:
        response = httpx.post(API_URL, json=PAYLOAD, timeout=TIMEOUT_SECONDS)
    except httpx.ConnectError:
        print("\nFAILED: nothing is listening on port 8000.")
        print("Start the server first:  uvicorn main:app --reload")
        return 1
    except httpx.TimeoutException:
        print(f"\nFAILED: no response within {TIMEOUT_SECONDS}s.")
        print("The first request loads the BAAI/bge-m3 model, which can take minutes.")
        return 1

    print("status:", response.status_code)
    if response.status_code != 200:
        print("body:", response.text[:2000])
        return 1

    data = response.json()
    print("\n--- response body ---")
    print(json.dumps(data, indent=2))

    print("\n--- checks ---")
    failures = []

    primary = data.get("primary_recommendations") or []
    primary_numbers = [r.get("is_number") for r in primary]
    ok = EXPECTED_IS in primary_numbers
    print("[{}] {} in primary_recommendations -> {}".format(
        "PASS" if ok else "FAIL", EXPECTED_IS, primary_numbers))
    if not ok:
        failures.append("{} missing from primary_recommendations".format(EXPECTED_IS))

    allied = data.get("allied_standards") or {}
    test_methods = allied.get(EXPECTED_ALLIED_KEY) or []
    allied_numbers = [a.get("is_number") for a in test_methods]
    ok = EXPECTED_ALLIED_IS in allied_numbers
    print("[{}] {} under allied_standards.{} -> {}".format(
        "PASS" if ok else "FAIL", EXPECTED_ALLIED_IS, EXPECTED_ALLIED_KEY, allied_numbers))
    if not ok:
        failures.append("{} missing from allied_standards.{}".format(
            EXPECTED_ALLIED_IS, EXPECTED_ALLIED_KEY))

    certs = data.get("certifications") or []
    cert_names = [c.get("scheme_name") for c in certs]
    ok = EXPECTED_CERT in cert_names
    print("[{}] {} in certifications -> {}".format(
        "PASS" if ok else "FAIL", EXPECTED_CERT, cert_names))
    if not ok:
        failures.append("{} missing from certifications".format(EXPECTED_CERT))

    print()
    if failures:
        print("RESULT: FAILED")
        for failure in failures:
            print("  -", failure)
        return 1

    print("RESULT: PASSED - all three checks succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
