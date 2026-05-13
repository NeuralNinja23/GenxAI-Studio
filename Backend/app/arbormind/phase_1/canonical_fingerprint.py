# canonical_fingerprint.py
#
# STEP 2: Three-layer fingerprint.
#
# Φ(V) = hash(structural + behavioral + semantic)
#
# The old fingerprint.py (FingerTrainer) hashes a dict.
# That's Layer 1 at best. It misses:
#   - Behavioral equivalence (same error, different syntax)
#   - Semantic equivalence (same meaning, different names)
#
# This module replaces structural-only hashing with
# a composite fingerprint that captures failure GEOMETRY,
# not just failure SYNTAX.
#
# ─── AUTHORITY SEPARATION ───
# SemanticTag (this file) = PRIMARY MEANING → feeds Φ (fingerprinting)
# FailureTaxonomy (phase_2) = SECONDARY GROUPING → feeds governance (mutation policy)
#
# SemanticTag answers: "What does this failure MEAN?"
# FailureTaxonomy answers: "What kind of failure IS this?"
#
# They must not conflict. If they do, SemanticTag wins for fingerprinting,
# FailureTaxonomy wins for governance.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import json


# ═══════════════════════════════════════════════════════════════
# SEMANTIC FAILURE TAGS
# ═══════════════════════════════════════════════════════════════
#
# These are the canonical semantic labels that map raw errors
# into meaning space. Two different errors that mean the same
# thing MUST map to the same tag.
#
# This is the hard part. And the important part.

class SemanticTag:
    """
    Canonical semantic failure categories.

    Rules:
    - Tags are strings (not enums) to allow extension
    - Each tag represents a MEANING, not a syntax
    - Multiple raw errors can map to the same tag
    """

    # ── Auth / Permission ──
    MISSING_AUTH_FIELD = "missing_auth_field"
    PERMISSION_DENIED = "permission_denied"
    INVALID_CREDENTIALS = "invalid_credentials"
    SESSION_EXPIRED = "session_expired"

    # ── Data / Schema ──
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_FIELD_TYPE = "invalid_field_type"
    FOREIGN_KEY_VIOLATION = "foreign_key_violation"
    UNIQUE_CONSTRAINT_VIOLATION = "unique_constraint_violation"
    SCHEMA_MISMATCH = "schema_mismatch"

    # ── Logic / Flow ──
    INVALID_STATE_TRANSITION = "invalid_state_transition"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    DEADLOCK = "deadlock"
    RACE_CONDITION = "race_condition"
    INFINITE_LOOP = "infinite_loop"

    # ── Integration ──
    API_CONTRACT_VIOLATION = "api_contract_violation"
    IMPORT_RESOLUTION_FAILURE = "import_resolution_failure"
    DEPENDENCY_MISSING = "dependency_missing"
    VERSION_INCOMPATIBILITY = "version_incompatibility"

    # ── UI / Interaction ──
    ELEMENT_NOT_FOUND = "element_not_found"
    INTERACTION_FAILURE = "interaction_failure"
    RENDER_FAILURE = "render_failure"
    LAYOUT_BROKEN = "layout_broken"

    # ── Runtime ──
    NULL_REFERENCE = "null_reference"
    INDEX_OUT_OF_BOUNDS = "index_out_of_bounds"
    TYPE_ERROR = "type_error"
    TIMEOUT = "timeout"
    MEMORY_EXHAUSTION = "memory_exhaustion"

    # ── Catch-all ──
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════
# SEMANTIC MAPPER
# ═══════════════════════════════════════════════════════════════

# Mapping rules: (pattern_in_error_string → semantic_tag)
# Order matters: first match wins.
# These are substring checks, NOT regex. Deterministic.

_SEMANTIC_RULES: List[Tuple[List[str], str]] = [
    # Auth
    (["role", "keyerror", "missing_role", "no role"], SemanticTag.MISSING_AUTH_FIELD),
    (["403", "forbidden", "permission denied", "access denied", "unauthorized"], SemanticTag.PERMISSION_DENIED),
    (["invalid password", "bad credentials", "authentication failed"], SemanticTag.INVALID_CREDENTIALS),
    (["session expired", "token expired", "jwt expired"], SemanticTag.SESSION_EXPIRED),

    # Data
    (["required field", "missing field", "field is required", "not null"], SemanticTag.MISSING_REQUIRED_FIELD),
    (["type error", "expected int", "expected str", "invalid type"], SemanticTag.INVALID_FIELD_TYPE),
    (["foreign key", "fk constraint", "referenced row"], SemanticTag.FOREIGN_KEY_VIOLATION),
    (["unique constraint", "duplicate key", "already exists"], SemanticTag.UNIQUE_CONSTRAINT_VIOLATION),
    (["schema", "column not found", "no such column", "table not found"], SemanticTag.SCHEMA_MISMATCH),

    # Logic
    (["invalid state", "illegal transition", "state machine"], SemanticTag.INVALID_STATE_TRANSITION),
    (["circular", "cycle detected", "circular dependency"], SemanticTag.CIRCULAR_DEPENDENCY),
    (["deadlock"], SemanticTag.DEADLOCK),
    (["race condition", "concurrent modification"], SemanticTag.RACE_CONDITION),
    (["infinite loop", "max recursion", "recursion depth"], SemanticTag.INFINITE_LOOP),

    # Integration
    (["contract", "api mismatch", "endpoint not found", "404"], SemanticTag.API_CONTRACT_VIOLATION),
    (["import error", "module not found", "no module named", "cannot import"], SemanticTag.IMPORT_RESOLUTION_FAILURE),
    (["dependency", "package not found", "pip install"], SemanticTag.DEPENDENCY_MISSING),
    (["version", "incompatible", "upgrade required"], SemanticTag.VERSION_INCOMPATIBILITY),

    # UI
    (["element not found", "selector", "no such element", "locator"], SemanticTag.ELEMENT_NOT_FOUND),
    (["not clickable", "not interactable", "disabled"], SemanticTag.INTERACTION_FAILURE),
    (["render", "paint", "dom exception"], SemanticTag.RENDER_FAILURE),
    (["layout", "overflow", "z-index", "position"], SemanticTag.LAYOUT_BROKEN),

    # Runtime
    (["nonetype", "null", "none", "undefined is not"], SemanticTag.NULL_REFERENCE),
    (["index out of range", "list index", "indexerror"], SemanticTag.INDEX_OUT_OF_BOUNDS),
    (["typeerror"], SemanticTag.TYPE_ERROR),
    (["timeout", "timed out", "deadline exceeded"], SemanticTag.TIMEOUT),
    (["memory", "oom", "out of memory"], SemanticTag.MEMORY_EXHAUSTION),
]


def classify_semantic_tag(
    error_type: str,
    error_message: str,
    stack_trace: str = "",
) -> str:
    """
    Map a raw error into semantic meaning space.

    Deterministic: same inputs → same tag, always.
    No LLM, no heuristics, no probability.
    """
    combined = f"{error_type} {error_message} {stack_trace}".lower()

    for patterns, tag in _SEMANTIC_RULES:
        for pattern in patterns:
            if pattern in combined:
                return tag

    return SemanticTag.UNKNOWN


# ═══════════════════════════════════════════════════════════════
# THREE-LAYER FINGERPRINT
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BehavioralTrace:
    """
    Layer 2: What actually happened at runtime.

    Two different code paths that produce the same error type
    at the same call path with the same failing condition
    are BEHAVIORALLY EQUIVALENT — even if the syntax differs.
    """
    error_type: str                     # e.g. "KeyError", "ImportError"
    call_path: List[str]                # e.g. ["auth.py", "validate_user"]
    failing_condition: str              # e.g. "missing_role"
    exit_code: Optional[int] = None     # process exit code if applicable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "call_path": self.call_path,
            "failing_condition": self.failing_condition,
            "exit_code": self.exit_code,
        }


@dataclass(frozen=True)
class CanonicalFingerprint:
    """
    Φ(V) — Three-layer canonical state fingerprint.

    Layer 1: Structural  — AST hash, dependency graph, code shape
    Layer 2: Behavioral  — execution trace, error type, call path
    Layer 3: Semantic     — failure meaning tag (maps syntax to meaning)

    The composite hash ensures:
    - Same code → same fingerprint (structural)
    - Same error from different code → same fingerprint (behavioral)
    - Same meaning from different errors → same fingerprint (semantic)
    """
    fingerprint_hash: str
    structural_hash: str
    behavioral_hash: str
    semantic_tag: str
    layers_present: List[str]           # which layers contributed


def _stable_hash(payload: Dict[str, Any]) -> str:
    """Deterministic, order-independent hash."""
    normalized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_structural_hash(
    signature: Dict[str, Any],
) -> str:
    """
    Layer 1: Pure structural hash.

    Input is the same dict you'd feed to the old FingerTrainer.
    This maintains backward compatibility while adding layers on top.
    """
    return _stable_hash(signature)


def compute_behavioral_hash(
    trace: BehavioralTrace,
) -> str:
    """
    Layer 2: Behavioral equivalence hash.

    Two different code paths that fail the same way
    produce the same behavioral hash.
    """
    return _stable_hash(trace.to_dict())


def compute_fingerprint(
    structural_signature: Dict[str, Any],
    behavioral_trace: Optional[BehavioralTrace] = None,
    error_type: str = "",
    error_message: str = "",
    stack_trace: str = "",
) -> CanonicalFingerprint:
    """
    Compute the three-layer canonical fingerprint Φ(V).

    This is the ONLY function external code should call.

    Args:
        structural_signature: Dict of structural properties (code shape, deps)
        behavioral_trace: Optional runtime execution trace
        error_type: Raw error class name (e.g. "KeyError")
        error_message: Raw error message
        stack_trace: Raw stack trace string

    Returns:
        CanonicalFingerprint with composite hash
    """
    layers_present: List[str] = ["structural"]

    # Layer 1: Structural
    struct_hash = compute_structural_hash(structural_signature)

    # Layer 2: Behavioral
    behav_hash = ""
    if behavioral_trace is not None:
        behav_hash = compute_behavioral_hash(behavioral_trace)
        layers_present.append("behavioral")

    # Layer 3: Semantic
    semantic = SemanticTag.UNKNOWN
    if error_type or error_message:
        semantic = classify_semantic_tag(error_type, error_message, stack_trace)
        layers_present.append("semantic")

    # Composite: hash of all three layers
    composite_payload = {
        "structural": struct_hash,
        "behavioral": behav_hash,
        "semantic": semantic,
    }
    composite_hash = _stable_hash(composite_payload)

    return CanonicalFingerprint(
        fingerprint_hash=composite_hash,
        structural_hash=struct_hash,
        behavioral_hash=behav_hash,
        semantic_tag=semantic,
        layers_present=layers_present,
    )
