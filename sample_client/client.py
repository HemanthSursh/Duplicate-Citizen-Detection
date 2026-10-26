"""Server-side HTTP adapter. Never send the API key to browser JavaScript."""
import os
import httpx


def call_api(operation, details):
    paths = {"check": "/api/v1/duplicates/check", "register": "/api/v1/customers/register"}
    if operation not in paths:
        raise ValueError("Unsupported operation")
    key = os.environ.get("CITIZEN_API_KEY", "")
    if len(key) < 32:
        raise ValueError("Configure CITIZEN_API_KEY on the sample-client server.")
    base = os.environ.get("CITIZEN_API_URL", "http://127.0.0.1:8000").rstrip("/")
    with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
        response = client.post(base + paths[operation], json=details, headers={"X-API-Key": key})
    if response.status_code not in (200, 201, 409):
        raise ValueError(f"API returned HTTP {response.status_code}; no success is confirmed.")
    result = response.json()
    if not isinstance(result, dict) or not isinstance(result.get("potential_duplicates"), bool) or not isinstance(result.get("candidates"), list):
        raise ValueError("Unexpected API response; no success is confirmed.")
    return response.status_code, result
