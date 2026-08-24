"""
Tier 3: Business Validation & Human-in-the-Loop (HITL).

Applies the confidence threshold theta = 0.95 from the blueprint, plus
basic field-completeness rules. Anything below threshold or with missing
mandatory fields is routed to PENDING_REVIEW rather than pushed straight
to core systems.
"""
from app.models import ExtractedPayload, ValidationResult, ValidationStatus

CONFIDENCE_THRESHOLD = 0.95
MANDATORY_FIELDS = ("client_name", "id_number", "policy_type")


def validate(payload: ExtractedPayload) -> ValidationResult:
    reasons: list[str] = []

    for field in MANDATORY_FIELDS:
        value = getattr(payload, field)
        if not value or value in ("UNKNOWN", "UNSPECIFIED"):
            reasons.append(f"Missing or unresolved field: {field}")

    if payload.confidence_score < CONFIDENCE_THRESHOLD:
        reasons.append(
            f"Confidence {payload.confidence_score:.2f} below threshold {CONFIDENCE_THRESHOLD:.2f}"
        )

    if reasons:
        status = ValidationStatus.PENDING_REVIEW
        reviewer_required = True
    else:
        status = ValidationStatus.VALIDATED
        reviewer_required = False

    return ValidationResult(
        payload=payload,
        status=status,
        threshold=CONFIDENCE_THRESHOLD,
        reasons=reasons,
        reviewer_required=reviewer_required,
    )
