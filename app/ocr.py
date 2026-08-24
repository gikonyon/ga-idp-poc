"""
Tier 2: AI Parsing & OCR Engine (simulation layer for the PoC).

In production this module would call a real OCR/IDP provider (e.g. AWS
Textract, Azure Document Intelligence, Google Document AI, or a
self-hosted layout-aware model). For this proof-of-concept it uses
deterministic, rule-based extraction from a mock "scanned" text payload
so the full pipeline can be demonstrated and tested end-to-end without
external dependencies or real customer data.

Swap `mock_extract()` for a real provider call to move from PoC to
production; the downstream contract (ExtractedPayload) does not change.
"""
import random
import re
from app.models import DocumentType, ExtractedPayload


def mock_extract(raw_text: str, document_type: DocumentType) -> ExtractedPayload:
    """Simulates OCR + field extraction from unstructured document text."""

    name_match = re.search(r"name[:\s]+([A-Za-z]+(?:\s[A-Za-z]+)*?)(?=\s+(?:ID|Policy|Phone)\b|$)", raw_text, re.IGNORECASE)
    id_match = re.search(r"\bid[:\s#]*([0-9]{6,10})", raw_text, re.IGNORECASE)
    policy_match = re.search(r"policy[:\s]+([A-Za-z0-9\s/]+?)(?=\s+(?:Phone|Branch|Date)\b|$)", raw_text, re.IGNORECASE)
    phone_match = re.search(r"(\+?254\d{9}|0\d{9})", raw_text)

    client_name = name_match.group(1).strip() if name_match else "UNKNOWN"
    id_number = id_match.group(1).strip() if id_match else "UNKNOWN"
    policy_type = policy_match.group(1).strip() if policy_match else "UNSPECIFIED"
    phone_number = phone_match.group(1).strip() if phone_match else None

    # Confidence model: penalise missing fields and short/noisy input.
    fields_found = sum([
        client_name != "UNKNOWN",
        id_number != "UNKNOWN",
        policy_type != "UNSPECIFIED",
    ])
    base_confidence = 0.60 + (fields_found * 0.13)
    noise_penalty = 0.05 if len(raw_text) < 40 else 0.0
    jitter = random.uniform(-0.02, 0.02)
    confidence_score = round(min(0.99, max(0.30, base_confidence - noise_penalty + jitter)), 2)

    return ExtractedPayload(
        client_name=client_name,
        id_number=id_number,
        policy_type=policy_type,
        phone_number=phone_number,
        document_type=document_type,
        confidence_score=confidence_score,
    )
