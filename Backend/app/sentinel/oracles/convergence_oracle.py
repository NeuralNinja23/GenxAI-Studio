# app/oracles/convergence_oracle.py
"""
V4 Convergence Oracle — Stage 4: Oracle Layer

SOFT Oracle serving as a thermodynamic monitor tracking branch convergence stability.
"""

from pathlib import Path
from typing import Any
import uuid

from app.core.logging import log
from app.sentinel.oracles.base import BaseOracle, OracleResult
from app.models.runtime_models import RuntimeTransaction

class ConvergenceOracle(BaseOracle):
    """
    Thermodynamic Stability Monitor (SOFT).
    Tracks entropy stability slopes and branches mutation frequency.
    Ensures branch stays stable or triggers deformation if stagnating.
    """

    def __init__(self):
        super().__init__(name="convergence_oracle", is_hard=False)

    async def validate(self, project_id: str, project_path: Path, cycle_ctx: Any) -> OracleResult:
        log("ORACLE", f"🔍 Running Convergence Oracle thermodynamic checks on {project_id}")

        # Fetch chronological transaction history from MongoDB
        history = await RuntimeTransaction.find(
            {"project_id": project_id},
            sort=[("started_at", 1)]
        ).to_list()

        entropy = 0.0
        stagnant_cycles = 0
        
        # Analyze stability slopes over last transactions
        if len(history) >= 2:
            prev_txs = history[-3:]
            # We measure how many consecutive transactions wrote the same set of files (stagnation)
            write_signatures = [sorted(tx.files_written) for tx in prev_txs]
            if len(write_signatures) >= 2 and all(sig == write_signatures[0] for sig in write_signatures):
                stagnant_cycles = len(write_signatures)
                entropy = 1.0  # High stagnation indicator

        evidence_key = f"ev-convergence-{str(uuid.uuid4())[:8]}"

        return OracleResult(
            passed=True,  # SOFT Oracle always passes cycle validation
            reason=f"Thermodynamic tracking finished (entropy={entropy:.2f}, stagnant_cycles={stagnant_cycles}).",
            metrics={"stagnation_cycles": stagnant_cycles, "system_entropy": entropy},
            evidence_key=evidence_key
        )
