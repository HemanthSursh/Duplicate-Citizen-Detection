"""Privacy-limited presentation of results from the existing matching engine."""
from .matching import FIELDS, match_reasons


def duplicate_response(matches):
    candidates = []
    for match in matches:
        reasons = match_reasons(match)
        candidates.append({
            "record_id": match["record"]["id"], "kind": match["kind"].lower().replace(" ", "_"),
            "similarity_score": match["score"], "field_scores": match["scores"],
            "matching_fields": match["matching_fields"],
            "differing_fields": [f for f in FIELDS if f not in match["matching_fields"]],
            "reasons": reasons, "recommended_next_step": "verify" if match["kind"] == "Exact" else "review",
        })
    return {"potential_duplicates": bool(candidates), "candidates": candidates,
            "recommended_next_step": "review" if candidates else "continue"}
