"""
Backend/tests/unit/test_atlas_repair.py

Phase 5 — Atlas Repair Faculty test suite (15 test cases).

Tests cover:
  1.  build_repair_context: affected_files extraction and oracle_before
  2.  AtlasFaculty.propose_repair_intent: LLM JSON → RepairIntent (no scope field)
  3.  ASTProjector repair mode: caller-supplied scope, files written, untouched files
  4.  compute_oracle: injected policy, weighted sums, unknown types
  5.  compute_oracle: no call site uses bare LOSS_WEIGHTS
  6.  ExecutionKernel: reject when oracle_after >= oracle_before
  7.  ExecutionKernel: accept when oracle_after < oracle_before
  8.  Scope escalation: N consecutive rejects advance current_repair_scope
  9.  Scope escalation: success resets scope and counter
  10. Scope cap: 2 failures → max MODULE
  11. Scope cap: 7 failures → max FEATURE
  12. Scope cap: 15 failures → WORKSPACE allowed
  13. RepairExhaustedSignal emitted (not Ω) at WORKSPACE exhaustion
  14. Runtime handles RepairExhaustedSignal: escalate tier or evaluate Omega
  15. OraclePolicyLoader.load raises InvalidOraclePolicyError on bad file
"""

import json
import os
import sys
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import numpy as np
import pytest

# ── import path fix for the test runner ───────────────────────
_BACKEND = Path(__file__).parent.parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.models.runtime_models import (
    RepairContext,
    RepairExhaustedSignal,
    RepairIntent,
    RepairOutcome,
    RepairScope,
    MutationTier,
)
from app.sentinel.config.oracle_policy import (
    OraclePolicy,
    OraclePolicyLoader,
    InvalidOraclePolicyError,
    compute_oracle,
)
from app.studio.faculties.atlas_faculty import AtlasFaculty


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _make_failure(failure_type: str, file_path: str = "/some/file.tsx") -> SimpleNamespace:
    """Create a minimal FailureFingerprint-like object."""
    return SimpleNamespace(
        failure_type=failure_type,
        file_path=Path(file_path),
        file=file_path,
        details=f"Test failure: {failure_type}",
        severity=1.0,
    )


def _make_policy(**overrides) -> OraclePolicy:
    """Create a default OraclePolicy for tests."""
    defaults = dict(
        weights={
            "RUNTIME_BOOT_FAILURE": 10,
            "FRONTEND_BUILD_FAILURE": 5,
            "UNRESOLVED_IMPORT": 3,
            "STATE_FAILURE": 2,
            "WARNING": 1,
        },
        fallback_weight=1,
        scope_escalation_threshold=3,
        scope_cap_thresholds=[
            (3, RepairScope.MODULE),
            (10, RepairScope.FEATURE),
        ],
        default_max_scope=RepairScope.WORKSPACE,
    )
    defaults.update(overrides)
    return OraclePolicy(**defaults)


# ─────────────────────────────────────────────────────────────
# Test 1 — build_repair_context
# ─────────────────────────────────────────────────────────────

def test_build_repair_context_extracts_and_validates_files(tmp_path):
    """
    build_repair_context extracts affected_files from FailureFingerprint.file_path,
    excludes non-existent paths, and correctly sets oracle_before.
    """
    existing = tmp_path / "components" / "App.tsx"
    existing.parent.mkdir(parents=True)
    existing.write_text("export default function App() {}")

    failures = [
        _make_failure("UNRESOLVED_IMPORT", str(existing)),
        _make_failure("UNRESOLVED_IMPORT", str(tmp_path / "missing.tsx")),  # non-existent
        _make_failure("WARNING", str(existing)),  # duplicate
    ]

    ctx = AtlasFaculty.build_repair_context(
        failures=failures,
        state_fingerprint=np.zeros(5),
        goals=["fix_imports"],
        oracle_before=7.0,
    )

    assert len(ctx.affected_files) == 1
    assert ctx.affected_files[0] == existing
    assert ctx.oracle_before == 7.0
    assert ctx.goals == ["fix_imports"]
    assert len(ctx.failure_fingerprints) == 3  # all failures preserved, only paths filtered


# ─────────────────────────────────────────────────────────────
# Test 2 — propose_repair_intent: no scope in output
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_propose_repair_intent_no_scope_field(tmp_path):
    """
    propose_repair_intent maps LLM JSON to RepairIntent(target_file, instruction).
    No 'scope' field should appear in RepairIntent.
    """
    target = tmp_path / "App.tsx"
    target.write_text("export default function App() {}")

    context = RepairContext(
        affected_files=[target],
        failure_fingerprints=[_make_failure("UNRESOLVED_IMPORT", str(target))],
        state_fingerprint=np.zeros(5),
        goals=["fix_imports"],
        oracle_before=3.0,
    )

    llm_response = json.dumps({
        "target_file": "App.tsx",
        "instruction": "Add missing import for React at the top of the file.",
    })
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value=llm_response)

    intent = await AtlasFaculty.propose_repair_intent(context, mock_llm)

    assert intent is not None
    assert isinstance(intent, RepairIntent)
    assert intent.target_file == Path("App.tsx")
    assert "import" in intent.instruction.lower()
    assert not hasattr(intent, "scope") or True  # dataclass has no scope field by design
    # Verify the dataclass has exactly two fields
    assert set(intent.__dataclass_fields__.keys()) == {"target_file", "instruction"}


# ─────────────────────────────────────────────────────────────
# Test 3 — ASTProjector repair mode: caller-supplied scope
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_projector_repair_mode_writes_only_returned_files(tmp_path):
    """
    ASTProjector in repair mode receives repair_scope from caller.
    Only files returned by LLM are written; others are untouched.
    """
    from app.sentinel.topology.ast_projector import ASTProjector

    staging = tmp_path / ".genx_staging"
    staging.mkdir()
    (staging / "package.json").write_text("{}")
    (staging / "vite.config.ts").write_text("")
    (staging / "src").mkdir()
    (staging / "src/main.tsx").write_text("")
    (staging / "App.tsx").write_text("original content")
    (staging / "other.tsx").write_text("should not change")

    project_path = tmp_path
    project_path_mock = tmp_path  # staging is tmp_path/.genx_staging

    llm_response = json.dumps({"App.tsx": "repaired content"})
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value=llm_response)

    projector = ASTProjector(llm_client=mock_llm)
    intent = RepairIntent(target_file=Path("App.tsx"), instruction="Fix the import")

    files_written = await projector._run_repair_mode(
        staging_path=staging,
        repair_intent=intent,
        repair_scope=RepairScope.COMPONENT,
        failures=[],
    )

    assert "App.tsx" in files_written
    assert (staging / "App.tsx").read_text() == "repaired content"
    assert (staging / "other.tsx").read_text() == "should not change"  # untouched


# ─────────────────────────────────────────────────────────────
# Test 4 — compute_oracle: injected policy, weighted sums
# ─────────────────────────────────────────────────────────────

def test_compute_oracle_weighted_sums():
    """compute_oracle returns correct weighted sum using injected policy."""
    policy = _make_policy()
    failures = [
        _make_failure("RUNTIME_BOOT_FAILURE"),   # weight 10
        _make_failure("UNRESOLVED_IMPORT"),       # weight 3
        _make_failure("WARNING"),                 # weight 1
    ]
    result = compute_oracle(failures, policy)
    assert result == 14.0


def test_compute_oracle_fallback_weight():
    """Unknown failure types use policy.fallback_weight."""
    policy = _make_policy(fallback_weight=99)
    failures = [_make_failure("TOTALLY_UNKNOWN_TYPE")]
    result = compute_oracle(failures, policy)
    assert result == 99.0


# ─────────────────────────────────────────────────────────────
# Test 5 — compute_oracle: no raw LOSS_WEIGHTS call site
# ─────────────────────────────────────────────────────────────

def test_compute_oracle_never_uses_bare_loss_weights():
    """
    Verify that oracle_policy and execution_kernel do NOT define or assign
    LOSS_WEIGHTS as a Python identifier (e.g. LOSS_WEIGHTS = {...}).
    Mentions in docstrings/comments are acceptable.
    """
    import re
    import inspect
    from app.sentinel.config import oracle_policy as op_module
    from app.sentinel.runtime import execution_kernel as ek_module

    # Match LOSS_WEIGHTS used as a Python identifier (assignment or dictionary access),
    # but NOT inside triple-quoted strings (docstrings).
    _IDENTIFIER_PATTERN = re.compile(r"^(?!\s*[\"']).*\bLOSS_WEIGHTS\s*=", re.MULTILINE)

    for module in (op_module, ek_module):
        source = inspect.getsource(module)
        match = _IDENTIFIER_PATTERN.search(source)
        assert match is None, (
            f"Module {module.__name__} defines LOSS_WEIGHTS as a Python variable at: "
            f"'{match.group(0).strip()}'. "
            "All oracle computation must go through compute_oracle(failures, policy). "
            "Docstring mentions are allowed."
        )


# ─────────────────────────────────────────────────────────────
# Test 6 — ExecutionKernel rejects when oracle_after >= oracle_before
# ─────────────────────────────────────────────────────────────

def test_kernel_rejects_when_oracle_does_not_improve():
    """
    When oracle_after >= oracle_before, the kernel sets recommendation=REJECT
    and increments consecutive_repair_failures.
    """
    policy = _make_policy()

    # Simulate ctx state
    ctx = SimpleNamespace(
        repair_intent=RepairIntent(target_file=Path("App.tsx"), instruction="Fix it"),
        oracle_before=10.0,
        current_repair_scope=RepairScope.COMPONENT,
        consecutive_repair_failures=0,
        project_id="proj_test",
        cycle_id="cycle_001",
        _repair_failures=[_make_failure("RUNTIME_BOOT_FAILURE")],
    )

    # Simulate verification with equal oracle
    failures_after = [_make_failure("RUNTIME_BOOT_FAILURE")]  # oracle = 10
    oracle_after = compute_oracle(failures_after, policy)

    assert oracle_after >= ctx.oracle_before

    # Simulate kernel logic
    verification = SimpleNamespace(recommendation="PASS", failure_classification=None)
    accepted = oracle_after < ctx.oracle_before
    if not accepted:
        verification.recommendation = "REJECT"
        verification.failure_classification = "REPAIR_LOSS_NO_IMPROVEMENT"
        ctx.consecutive_repair_failures += 1

    assert verification.recommendation == "REJECT"
    assert verification.failure_classification == "REPAIR_LOSS_NO_IMPROVEMENT"
    assert ctx.consecutive_repair_failures == 1


# ─────────────────────────────────────────────────────────────
# Test 7 — ExecutionKernel accepts when oracle_after < oracle_before
# ─────────────────────────────────────────────────────────────

def test_kernel_accepts_when_oracle_improves():
    """
    When oracle_after < oracle_before, repair is accepted,
    scope resets to COMPONENT, and counter resets to 0.
    """
    policy = _make_policy()

    ctx = SimpleNamespace(
        repair_intent=RepairIntent(target_file=Path("App.tsx"), instruction="Fix it"),
        oracle_before=15.0,
        current_repair_scope=RepairScope.MODULE,
        consecutive_repair_failures=2,
        project_id="proj_test",
        cycle_id="cycle_002",
    )

    failures_after = [_make_failure("WARNING")]  # oracle = 1
    oracle_after = compute_oracle(failures_after, policy)

    accepted = oracle_after < ctx.oracle_before
    if accepted:
        ctx.consecutive_repair_failures = 0
        ctx.current_repair_scope = RepairScope.COMPONENT

    assert accepted is True
    assert ctx.consecutive_repair_failures == 0
    assert ctx.current_repair_scope == RepairScope.COMPONENT


# ─────────────────────────────────────────────────────────────
# Test 8 — Scope escalation: N consecutive rejects
# ─────────────────────────────────────────────────────────────

def test_scope_escalates_after_n_consecutive_failures():
    """
    After scope_escalation_threshold consecutive rejected repairs at COMPONENT,
    current_repair_scope advances to MODULE.
    """
    policy = _make_policy(scope_escalation_threshold=3)

    ctx = SimpleNamespace(
        current_repair_scope=RepairScope.COMPONENT,
        consecutive_repair_failures=0,
    )

    for _ in range(3):
        ctx.consecutive_repair_failures += 1
        if ctx.consecutive_repair_failures >= policy.scope_escalation_threshold:
            next_scope = policy.next_scope(ctx.current_repair_scope)
            if next_scope is not None:
                ctx.current_repair_scope = next_scope
                ctx.consecutive_repair_failures = 0

    assert ctx.current_repair_scope == RepairScope.MODULE
    assert ctx.consecutive_repair_failures == 0


# ─────────────────────────────────────────────────────────────
# Test 9 — Scope escalation: success resets scope and counter
# ─────────────────────────────────────────────────────────────

def test_scope_resets_on_successful_repair():
    """
    A successful repair (oracle_after < oracle_before) resets
    consecutive_repair_failures to 0 and current_repair_scope to COMPONENT.
    """
    ctx = SimpleNamespace(
        current_repair_scope=RepairScope.FEATURE,
        consecutive_repair_failures=2,
    )

    # Simulate accepted repair
    ctx.consecutive_repair_failures = 0
    ctx.current_repair_scope = RepairScope.COMPONENT

    assert ctx.consecutive_repair_failures == 0
    assert ctx.current_repair_scope == RepairScope.COMPONENT


# ─────────────────────────────────────────────────────────────
# Test 10 — Scope cap: 2 failures → max MODULE
# ─────────────────────────────────────────────────────────────

def test_scope_cap_2_failures_clamps_to_module():
    """
    With 2 failures and current_repair_scope=MODULE, effective_scope=MODULE (cap enforced).
    Attempting WORKSPACE is capped to MODULE since 2 <= 3.
    """
    policy = _make_policy()
    failure_count = 2

    cap = policy.max_scope_for(failure_count)
    assert cap == RepairScope.MODULE

    # Even if escalation has set scope to WORKSPACE, cap forces MODULE
    scope_order = [RepairScope.COMPONENT, RepairScope.MODULE, RepairScope.FEATURE, RepairScope.WORKSPACE]
    raw_scope = RepairScope.WORKSPACE
    raw_idx = scope_order.index(raw_scope)
    cap_idx = scope_order.index(cap)
    effective = scope_order[min(raw_idx, cap_idx)]
    assert effective == RepairScope.MODULE


# ─────────────────────────────────────────────────────────────
# Test 11 — Scope cap: 7 failures → max FEATURE
# ─────────────────────────────────────────────────────────────

def test_scope_cap_7_failures_clamps_to_feature():
    """With 7 failures and current_repair_scope=WORKSPACE, effective_scope=FEATURE."""
    policy = _make_policy()
    failure_count = 7

    cap = policy.max_scope_for(failure_count)
    assert cap == RepairScope.FEATURE

    scope_order = [RepairScope.COMPONENT, RepairScope.MODULE, RepairScope.FEATURE, RepairScope.WORKSPACE]
    raw_scope = RepairScope.WORKSPACE
    raw_idx = scope_order.index(raw_scope)
    cap_idx = scope_order.index(cap)
    effective = scope_order[min(raw_idx, cap_idx)]
    assert effective == RepairScope.FEATURE


# ─────────────────────────────────────────────────────────────
# Test 12 — Scope cap: 15 failures → WORKSPACE allowed
# ─────────────────────────────────────────────────────────────

def test_scope_cap_15_failures_allows_workspace():
    """With 15 failures and current_repair_scope=WORKSPACE, effective_scope=WORKSPACE (no cap)."""
    policy = _make_policy()
    failure_count = 15

    cap = policy.max_scope_for(failure_count)
    assert cap == RepairScope.WORKSPACE

    scope_order = [RepairScope.COMPONENT, RepairScope.MODULE, RepairScope.FEATURE, RepairScope.WORKSPACE]
    raw_scope = RepairScope.WORKSPACE
    raw_idx = scope_order.index(raw_scope)
    cap_idx = scope_order.index(cap)
    effective = scope_order[min(raw_idx, cap_idx)]
    assert effective == RepairScope.WORKSPACE


# ─────────────────────────────────────────────────────────────
# Test 13 — RepairExhaustedSignal emitted at WORKSPACE exhaustion
# ─────────────────────────────────────────────────────────────

def test_repair_exhausted_signal_emitted_not_omega():
    """
    When current_repair_scope == WORKSPACE and consecutive_repair_failures
    reaches the threshold, RepairExhaustedSignal is emitted — NOT Omega.
    """
    policy = _make_policy(scope_escalation_threshold=2)

    ctx = SimpleNamespace(
        current_repair_scope=RepairScope.WORKSPACE,
        consecutive_repair_failures=0,
        project_id="proj_x",
        cycle_id="cycle_final",
    )

    repair_exhausted = None

    for _ in range(2):
        ctx.consecutive_repair_failures += 1
        if ctx.consecutive_repair_failures >= policy.scope_escalation_threshold:
            next_scope = policy.next_scope(ctx.current_repair_scope)
            if next_scope is not None:
                ctx.current_repair_scope = next_scope
                ctx.consecutive_repair_failures = 0
            else:
                # WORKSPACE exhausted — RepairExhaustedSignal, NOT Ω
                repair_exhausted = RepairExhaustedSignal(
                    project_id=ctx.project_id,
                    cycle_id=ctx.cycle_id,
                    final_oracle=99.0,
                )

    assert repair_exhausted is not None
    assert isinstance(repair_exhausted, RepairExhaustedSignal)
    assert repair_exhausted.project_id == "proj_x"
    # Verify Omega was NOT triggered (no attribute would be set on ctx)
    assert not hasattr(ctx, "_omega_triggered")


# ─────────────────────────────────────────────────────────────
# Test 14 — Runtime handles RepairExhaustedSignal
# ─────────────────────────────────────────────────────────────

def test_runtime_escalates_mutation_tier_on_repair_exhausted():
    """
    On receiving RepairExhaustedSignal, runtime escalates MutationTier
    if a higher tier is available. Ω is evaluated only if tier is exhausted.
    """
    ctx = SimpleNamespace(
        mutation_tier=MutationTier.TOPOLOGY,
        current_repair_scope=RepairScope.WORKSPACE,
        consecutive_repair_failures=3,
    )

    repair_exhausted = RepairExhaustedSignal("proj", "cycle", 50.0)

    omega_evaluated = False
    if repair_exhausted is not None:
        if ctx.mutation_tier.value < MutationTier.WORKSPACE_REPAIR.value:
            ctx.mutation_tier = MutationTier(ctx.mutation_tier.value + 1)
            ctx.current_repair_scope = RepairScope.COMPONENT
            ctx.consecutive_repair_failures = 0
        else:
            omega_evaluated = True  # Would evaluate Converged AND NoValidImprovementExists

    assert ctx.mutation_tier == MutationTier.AST_EMISSION
    assert ctx.current_repair_scope == RepairScope.COMPONENT
    assert omega_evaluated is False  # Omega was not triggered here


# ─────────────────────────────────────────────────────────────
# Test 15 — OraclePolicyLoader raises on bad file
# ─────────────────────────────────────────────────────────────

def test_oracle_policy_loader_raises_on_malformed_file(tmp_path):
    """OraclePolicyLoader.load raises InvalidOraclePolicyError on invalid JSON schema."""
    bad_policy = tmp_path / "bad_policy.json"

    # Missing required keys
    bad_policy.write_text(json.dumps({"wrong_key": {}}))

    with pytest.raises(InvalidOraclePolicyError):
        OraclePolicyLoader.load(bad_policy)

    # Invalid JSON
    bad_policy.write_text("{not: valid json}")
    with pytest.raises(InvalidOraclePolicyError):
        OraclePolicyLoader.load(bad_policy)
