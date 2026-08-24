import json
from app.config import CONFIDENCE_THRESHOLD
from app.models import AuditLogModel

def parse_document_text(raw_text: str, document_type: str):
    """Simulates OCR extraction and intelligent parsing into structured data."""
    extracted_data = {}
    parts = raw_text.split()
    
    # Simple extraction logic mock based on keywords
    text_lower = raw_text.lower()
    if "name:" in text_lower:
        extracted_data["name"] = "Jane Wanjiku"
    if "id:" in text_lower:
        extracted_data["id_number"] = "32145678"
    if "policy:" in text_lower:
        extracted_data["policy"] = "Life Assurance"
    if "phone:" in text_lower:
        extracted_data["phone"] = "0722334455"
        
    # Default confidence score simulation
    confidence = 0.96 if len(extracted_data) >= 3 else 0.85
    status = "APPROVED" if confidence >= CONFIDENCE_THRESHOLD else "FLAGGED_FOR_REVIEW"
    
    return {
        "document_type": document_type,
        "extracted_data": extracted_data,
        "confidence_score": confidence,
        "status": status,
        "message": "Passed automated validation" if status == "APPROVED" else "Below confidence threshold; review required."
    }

def log_audit_event(db, event_type: str, document_type: str, status: str, payload: dict):
    """Logs middleware transactions to the SQLite audit database."""
    log_entry = AuditLogModel(
        event_type=event_type,
        document_type=document_type,
        status=status,
        payload=json.dumps(payload)
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry