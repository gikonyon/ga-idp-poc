# GA-IDP Gateway — Proof of Concept

**Prepared for:** GA Insurance Limited (Sheila Mwai and technical stakeholders)
**Purpose:** A complete, runnable proof-of-concept of the Intelligent Document
Processing (IDP) and RPA middleware layer described in the *GA Insurance
Technical Integration Blueprint*.

A companion PDF (`GA-IDP-Gateway-Technical-Walkthrough.pdf`) documents the
step-by-step application flow and explains what every function in this
repository does and why.

## What this proves

| Tier | Blueprint Requirement | This PoC |
|---|---|---|
| 1. Ingestion | REST endpoints for unstructured documents | `POST /api/v1/extract-registration` |
| 2. OCR/Parsing | Structured JSON extraction, confidence scoring | `app/ocr.py` |
| 3. Validation / HITL | Route below θ=0.95 confidence to human review | `app/validation.py` + `app/database.py` review queue + `/review` dashboard |
| 4. Core Connectors | Push validated data to SAP/Oracle/cloud | `app/connectors.py` |
| Security baseline (Step 1) | RBAC, encrypted transit | `app/auth.py` (API-key layer), HTTPS-ready via reverse proxy |
| Audit trail | Immutable logging | `app/database.py` — append-only `audit_log` table |

Every payload that fails validation is written to a **review queue** and
blocked from reaching core systems (`HTTP 409`) until a human resolves it
through the `/review` dashboard.

## What's included (nothing mocked-out silently)

```
ga-idp-poc/
├── app/
│   ├── main.py          # FastAPI app: routes, wiring, lifespan startup
│   ├── config.py          # Environment-driven settings (Settings dataclass)
│   ├── auth.py             # API-key dependency (RBAC seam)
│   ├── database.py         # SQLite persistence: audit_log + review_queue
│   ├── models.py           # Pydantic data contracts shared across tiers
│   ├── ocr.py               # Tier 2: extraction + confidence scoring
│   ├── validation.py        # Tier 3: HITL threshold enforcement
│   ├── connectors.py        # Tier 4: SAP/Oracle/cloud push adapters
│   └── templates/
│       └── review.html      # HITL review dashboard (Jinja2)
├── tests/
│   └── test_pipeline.py     # 12 tests: unit, auth, persistence, dashboard
├── sample_docs/
│   └── sample_registration.txt
├── .github/workflows/tests.yml   # CI: runs pytest on every push
├── .env.example                  # All configurable variables, documented
├── docker-compose.yml             # One-command local/pilot deployment
├── Dockerfile
├── requirements.txt
└── README.md
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the API (auth is ON by default — see .env.example)
export GA_IDP_API_KEY=demo-key-change-me
uvicorn app.main:app --reload --port 8000

# Open http://127.0.0.1:8000/docs   — interactive Swagger UI
# Open http://127.0.0.1:8000/review — HITL review dashboard

# Run the full test suite
pytest -v
```

Or with Docker Compose:
```bash
docker compose up --build
```

## Demo walkthrough

1. **Ingest a clean document** — returns `VALIDATED` immediately:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/extract-registration \
     -H "Content-Type: application/json" -H "X-API-Key: demo-key-change-me" \
     -d '{"raw_text": "Name: Jane Wanjiku ID: 32145678 Policy: Life Assurance Phone: 0722334455", "document_type": "registration_form"}'
   ```

2. **Ingest a noisy/incomplete document** — returns `PENDING_REVIEW` with
   explicit reasons, and the item appears on the `/review` dashboard for a
   human to approve or reject.

3. **Push a validated payload to a core system:**
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/push-to-core \
     -H "Content-Type: application/json" -H "X-API-Key: demo-key-change-me" \
     -d '{"validation_result": <result from step 1>, "target": "sap_hana"}'
   ```
   A `PENDING_REVIEW` payload is rejected with `409 Conflict`.

4. **Check the audit trail:**
   ```bash
   curl http://127.0.0.1:8000/api/v1/audit-log -H "X-API-Key: demo-key-change-me"
   ```

## From PoC to production

- **OCR engine:** `mock_extract()` in `app/ocr.py` → a real provider call
  (AWS Textract, Azure Document Intelligence, Google Document AI).
- **Auth:** the single shared API key in `app/auth.py` → GA's real identity
  provider issuing scoped tokens.
- **Connectors:** `app/connectors.py` mocks → real SAP PO OData calls, OIC
  REST adapters, and Snowflake/BigQuery + Kafka triggers using GA credentials.
- **Database:** SQLite (`app/database.py`) → Postgres/managed DB; the calling
  code does not change, since all access already goes through this module.

## Suggested next steps with GA Insurance

1. Walkthrough demo with Sheila's technical team (30–45 min), live on the
   `/review` dashboard.
2. Confirm target core system priority (SAP HANA vs Oracle Cloud vs cloud
   warehouse) to scope the first real connector.
3. Identify a real (anonymised) sample of registration/claim documents to
   validate the confidence model against GA's actual document quality.
4. Agree scope for a shadow-mode pilot per the blueprint's Step 4 timeline.
