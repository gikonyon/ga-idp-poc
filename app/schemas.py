from pydantic import BaseModel
from typing import Dict, Any, Optional

class ExtractionRequest(BaseModel):
    raw_text: str
    document_type: str

class ValidationResult(BaseModel):
    document_type: str
    extracted_data: Dict[str, Any]
    confidence_score: float
    status: str
    message: Optional[str] = None

class CorePushRequest(BaseModel):
    validation_result: ValidationResult
    target: str