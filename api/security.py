"""One environment-configured key grants access to this entire local registry."""
import os
import secrets
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: str | None = Security(key_header)):
    expected = os.environ.get("CITIZEN_API_KEY", "")
    if len(expected) < 32:
        raise HTTPException(503, "API authentication is not configured.")
    if provided is None or not secrets.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(401, "Invalid or missing API key.")
