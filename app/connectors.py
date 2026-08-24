"""
Tier 4: Enterprise System Connectors.

Each function simulates pushing a validated payload into a target core
system, using the interface pattern named in the blueprint:
  - SAP HANA / SAP ERP  -> SAP PO OData services -> KNA1 / KNB1 tables
  - Oracle Cloud ERP     -> Oracle Integration Cloud (OIC) REST adapters
  - Cloud warehouses     -> Snowflake / BigQuery + Kafka event trigger

Only VALIDATED payloads should reach these connectors; PENDING_REVIEW
payloads must be resolved by a human reviewer first (see validation.py).
"""
import uuid
from app.models import CorePushResult, CoreTarget, ValidationResult, ValidationStatus


def push_to_core(result: ValidationResult, target: CoreTarget) -> CorePushResult:
    if result.status != ValidationStatus.VALIDATED:
        return CorePushResult(
            target=target,
            accepted=False,
            message="Blocked: payload has not passed validation (HITL review required).",
        )

    external_reference = f"{target.value.upper()}-{uuid.uuid4().hex[:10]}"

    if target == CoreTarget.SAP_HANA:
        message = "Mapped to SAP PO OData service; written to KNA1/KNB1 customer master tables."
    elif target == CoreTarget.ORACLE_CLOUD:
        message = "Pushed via Oracle Integration Cloud (OIC) REST adapter to underwriting ledger."
    else:
        message = "Written to cloud data lake (Snowflake/BigQuery); Kafka notification triggered."

    return CorePushResult(
        target=target,
        accepted=True,
        external_reference=external_reference,
        message=message,
    )
