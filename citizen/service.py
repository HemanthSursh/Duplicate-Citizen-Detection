"""Privacy-limited presentation of results from the existing matching engine."""
from .matching import FIELDS, THRESHOLD


def duplicate_response(matches):
    candidates = []
    for match in matches:
        reasons = (["All four normalized fields have the same SHA-256 fingerprint."]
                   if match["kind"] == "Exact" else
                   [f"Weighted similarity {match['score']}/100 meets the {THRESHOLD}/100 threshold.",
                    f"Name similarity {match['scores']['full_name']}/100 meets the 65/100 name guard."])
        candidates.append({
            "record_id": match["record"]["id"], "kind": match["kind"].lower(),
            "similarity_score": match["score"], "field_scores": match["scores"],
            "matching_fields": match["matching_fields"],
            "differing_fields": [f for f in FIELDS if f not in match["matching_fields"]],
            "reasons": reasons, "recommended_next_step": "verify" if match["kind"] == "Exact" else "review",
        })
    return {"potential_duplicates": bool(candidates), "candidates": candidates,
            "recommended_next_step": "review" if candidates else "continue"}
