"""Optional fictional references only, never real identity-document numbers."""
import re
from .matching import clean_text

DOCUMENT_FIELDS = ("aadhaar_ref", "licence_ref")


def validate_documents(data):
    result = {}
    for field, prefix in (("aadhaar_ref", "DEMO-AAD-"), ("licence_ref", "DEMO-DL-")):
        value = clean_text(data.get(field, "")).upper()
        if value and not re.fullmatch(re.escape(prefix) + r"[A-Z0-9-]{1,24}", value):
            raise ValueError(f"Use only fictional references beginning {prefix}. Do not enter a real document number.")
        result[field] = value
    return result
