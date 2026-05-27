# app/governance/evidence_registry.py
"""
V4 Epistemic Grounding Registry — Stage 4: Oracle Layer

Defines the Beanie collection and engine for registering validation traces,
screenshot paths, and logs to verify claims mathematically.
"""

from datetime import datetime
from typing import Dict, List, Optional
from beanie import Document, Indexed
from pydantic import Field
import uuid

from app.core.time import utc_now

# ─────────────────────────────────────────────────────────────
# 1. Beanie Persistence Model for Evidence Ledger
# ─────────────────────────────────────────────────────────────

class EvidenceRecord(Document):
    """
    Epistemic Grounding Ledger entry.
    All claims of operational success must register physical evidence traces here.
    """
    evidence_key: Indexed(str, unique=True)
    project_id: Indexed(str)
    claim_type: str                  # e.g. "syntax", "topology", "behavioral", "runtime", "visual"
    evidence_payload: Dict           # logs, traces, checksums
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "evidence_records"


# ─────────────────────────────────────────────────────────────
# 2. Evidence Registry Engine
# ─────────────────────────────────────────────────────────────

class EvidenceRegistry:
    """
    Epistemic Grounding Ledger Engine.
    Ensures no cognitive or executor faculty can claim 'success' without verified trace validation.
    """

    @staticmethod
    async def register_evidence(
        project_id: str,
        claim_type: str,
        evidence_payload: Dict,
        custom_key: Optional[str] = None
    ) -> str:
        """Record physical trace evidence and return a secure key."""
        evidence_key = custom_key or f"ev-ground-{uuid.uuid4()}"
        
        record = EvidenceRecord(
            evidence_key=evidence_key,
            project_id=project_id,
            claim_type=claim_type,
            evidence_payload=evidence_payload
        )
        await record.insert()
        return evidence_key

    @staticmethod
    async def verify_evidence_key(evidence_key: str) -> bool:
        """Verify that the given evidence key exists in the ledger."""
        record = await EvidenceRecord.find_one(
            EvidenceRecord.evidence_key == evidence_key
        )
        return record is not None

    @staticmethod
    async def get_evidence(evidence_key: str) -> Optional[EvidenceRecord]:
        """Fetch the registered evidence trace data for the given key."""
        return await EvidenceRecord.find_one(
            EvidenceRecord.evidence_key == evidence_key
        )
