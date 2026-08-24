"""
Tests covering the full Tier 1-4 pipeline, plus persistence, API-key
auth, and the HITL review dashboard/approval flow.

GA_IDP_DB_PATH is pointed at a throwaway file and GA_IDP_API_KEY is set
to a known test value *before* importing the app, so config.settings
picks them up at import time.
"""
import os
import sys

TEST_DB_PATH = "test_ga_idp.db"
os.environ["GA_IDP_DB_PATH"] = TEST_DB_PATH
os.environ["GA_IDP_API_KEY"] = "test-key-123"
os.environ["GA_IDP_REQUIRE_AUTH"] = "true"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import DocumentType, CoreTarget, ValidationStatus
from app.ocr import mock_extract
from app.validation import validate
from app.connectors import push_to_core
from app import database

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "test-key-123"}

CLEAN_TEXT = "Name: Jane Wanjiku ID: 32145678 Policy: Life Assurance Phone: 0722334455"
NOISY_TEXT = "smudged scan ///"


@pytest.fixture(autouse=True, scope="function")
def clean_db():
    """Ensures each test starts against a fresh SQLite file."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    database.init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


# --- Unit-level pipeline logic (no HTTP layer) -----------------------------

def test_extraction_with_clean_input_has_high_confidence():
    payload = mock_extract(CLEAN_TEXT, DocumentType.REGISTRATION_FORM)
    assert payload.client_name == "Jane Wanjiku"
    assert payload.id_number == "32145678"
    assert payload.confidence_score > 0.7


def test_extraction_with_noisy_input_flags_missing_fields():
    payload = mock_extract(NOISY_TEXT, DocumentType.REGISTRATION_FORM)
    result = validate(payload)
    assert result.status == ValidationStatus.PENDING_REVIEW
    assert result.reviewer_required is True
    assert len(result.reasons) > 0


def test_validated_payload_can_push_to_sap():
    payload = mock_extract(CLEAN_TEXT, DocumentType.REGISTRATION_FORM)
    payload.confidence_score = 0.97  # force above threshold for deterministic test
    result = validate(payload)
    assert result.status == ValidationStatus.VALIDATED

    push_result = push_to_core(result, CoreTarget.SAP_HANA)
    assert push_result.accepted is True
    assert push_result.external_reference.startswith("SAP_HANA-")


def test_pending_review_payload_blocked_from_core_push():
    payload = mock_extract(NOISY_TEXT, DocumentType.REGISTRATION_FORM)
    result = validate(payload)
    push_result = push_to_core(result, CoreTarget.ORACLE_CLOUD)
    assert push_result.accepted is False


# --- API-level: auth enforcement -------------------------------------------

def test_extract_endpoint_rejects_missing_api_key():
    resp = client.post(
        "/api/v1/extract-registration",
        json={"raw_text": CLEAN_TEXT, "document_type": "registration_form"},
    )
    assert resp.status_code == 401


def test_extract_endpoint_rejects_wrong_api_key():
    resp = client.post(
        "/api/v1/extract-registration",
        json={"raw_text": CLEAN_TEXT, "document_type": "registration_form"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


# --- API-level: happy path + persistence -----------------------------------

def test_api_extract_endpoint_with_valid_key():
    resp = client.post(
        "/api/v1/extract-registration",
        json={"raw_text": CLEAN_TEXT, "document_type": "registration_form"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["payload"]["client_name"] == "Jane Wanjiku"

    # Confirm the event was written to the audit log
    audit_resp = client.get("/api/v1/audit-log", headers=AUTH_HEADERS)
    assert audit_resp.status_code == 200
    assert audit_resp.json()["count"] >= 1


def test_api_push_blocked_when_reviewer_required():
    extract_resp = client.post(
        "/api/v1/extract-registration",
        json={"raw_text": NOISY_TEXT, "document_type": "registration_form"},
        headers=AUTH_HEADERS,
    )
    validation_result = extract_resp.json()
    push_resp = client.post(
        "/api/v1/push-to-core",
        json={"validation_result": validation_result, "target": "sap_hana"},
        headers=AUTH_HEADERS,
    )
    assert push_resp.status_code == 409


# --- HITL review queue + dashboard ------------------------------------------

def test_noisy_extraction_lands_in_review_queue():
    client.post(
        "/api/v1/extract-registration",
        json={"raw_text": NOISY_TEXT, "document_type": "registration_form"},
        headers=AUTH_HEADERS,
    )
    open_reviews = database.list_open_reviews()
    assert len(open_reviews) == 1


def test_review_dashboard_renders():
    client.post(
        "/api/v1/extract-registration",
        json={"raw_text": NOISY_TEXT, "document_type": "registration_form"},
        headers=AUTH_HEADERS,
    )
    resp = client.get("/review")
    assert resp.status_code == 200
    assert "Review" in resp.text


def test_approve_review_marks_it_resolved():
    client.post(
        "/api/v1/extract-registration",
        json={"raw_text": NOISY_TEXT, "document_type": "registration_form"},
        headers=AUTH_HEADERS,
    )
    review_id = database.list_open_reviews()[0]["id"]

    resp = client.post(f"/review/{review_id}/approve", follow_redirects=False)
    assert resp.status_code == 303
    assert database.list_open_reviews() == []


def test_reject_unknown_review_returns_404():
    resp = client.post("/review/9999/reject")
    assert resp.status_code == 404
