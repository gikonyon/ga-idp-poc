from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.config import API_KEY, CONFIDENCE_THRESHOLD
from app.database import engine, Base, get_db
from app.schemas import ExtractionRequest, ValidationResult, CorePushRequest
from app.services import parse_document_text, log_audit_event
from app.models import AuditLogModel

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GA-IDP Gateway API",
    description="Intelligent Document Processing & RPA Middleware Layer",
    version="1.0.0"
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key"
    )

@app.post("/api/v1/extract-registration", response_model=ValidationResult)
def extract_and_validate(payload: ExtractionRequest, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    result = parse_document_text(payload.raw_text, payload.document_type)
    log_audit_event(db, "EXTRACTION_AND_VALIDATION", payload.document_type, result["status"], result)
    return result

@app.post("/api/v1/push-to-core")
def push_to_core(payload: CorePushRequest, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    val = payload.validation_result
    if val.confidence_score < CONFIDENCE_THRESHOLD or val.status != "APPROVED":
        log_audit_event(db, "CORE_PUSH_BLOCKED", val.document_type, "CONFLICT_409", payload.dict())
        raise HTTPException(
            status_code=409,
            detail="Payload flagged below threshold; requires HITL resolution before core sync."
        )
    
    response_data = {
        "status": "SUCCESS",
        "target_system": payload.target,
        "message": f"Successfully synced payload to {payload.target}"
    }
    log_audit_event(db, "CORE_PUSH_SUCCESS", val.document_type, "SYNCED", response_data)
    return response_data

@app.get("/review", response_class=HTMLResponse)
def review_queue(api_key: str = Depends(verify_api_key)):
    return """
    <html>
        <head><title>GA-IDP Review Queue</title></head>
        <body style="font-family: Arial; padding: 40px; background: #f4f6f8;">
            <h2>⚖️ GA-IDP Human-in-the-Loop Exception Queue</h2>
            <p>No pending flagged documents requiring manual review at this time.</p>
        </body>
    </html>
    """

@app.get("/api/v1/audit-log")
def get_audit_logs(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    logs = db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).all()
    entries = []
    for log in logs:
        entries.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "event_type": log.event_type,
            "document_type": log.document_type,
            "status": log.status,
            "payload": log.payload
        })
    return {"count": len(entries), "entries": entries}
