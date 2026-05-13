# ArborMind Implementation Plan
**Based on: ArborMind Research.txt (1136 lines)**  
**Target Architecture: Backend/app/arbormind/**  
**Date: 2025-12-28**

---

## Table of Contents
1. [Overview](#overview)
2. [Core Mathematical Components](#core-mathematical-components)
3. [Module-by-Module Breakdown](#module-by-module-breakdown)
4. [Data Structures](#data-structures)
5. [Integration Points](#integration-points)
6. [Implementation Phases](#implementation-phases)
7. [Testing Strategy](#testing-strategy)

---

## Overview

### Goal
Implement ArborMind as a control-theoretic AGI layer that transforms FAST V2 from a linear orchestrator into a governed, self-healing system capable of:
- Autonomous error correction
- Cross-project failure learning
- Architectural mutation
- Formal convergence guarantees

### Design Principles (from Appendix F)
1. **Strict Authority Separation**: LLM actuates, Governor controls
2. **Deterministic Execution**: Same inputs → same outputs
3. **Global Memory**: Persistent failure set across projects
4. **Multimodal Truth**: Static + Logical + Visual validation
5. **Hard Stop Condition**: Ω = (L=0) ∧ (Δα < ε)

---

## Core Mathematical Components

### 1. State Representation (Section 5.1)
```
S_t = (V_t, K_t, Q_t, F)

where:
- V_t: Executable software artifact (code, config, schema, assets)
- K_t: Semantic representation (domain rules, invariants)
- Q_t: Current intent/objective
- F: Global Failure Set
```

### 2. Control Equation (Section 6)
```
α(Q,K) = Softmax(QK^T/√d_k) - λ∑(i∈F) Kernel(dist(K, K_i))
```

### 3. Convergence Condition (Section 8)
```
Ω ⟺ (L=0) ∧ (Δα(Q,K) < ε)
```

---

## Module-by-Module Breakdown

### Module 1: `state.py` - V Snapshot Abstraction

**Purpose**: Represent software state at time t

**Core Classes**:
```python
@dataclass
class SoftwareState:
    """V_t - Executable artifact state"""
    timestamp: datetime
    project_id: str
    code_files: Dict[str, str]           # path → content
    config_files: Dict[str, str]         # path → content
    schema: Optional[str]                # DB schema
    assets: Dict[str, bytes]             # static assets
    git_hash: Optional[str]              # version control
    
@dataclass
class SemanticKey:
    """K_t - Non-code truth"""
    domain_schema: Dict[str, Any]        # Entity relationships
    business_rules: List[str]            # Invariants
    security_constraints: List[str]      # RBAC, auth rules
    ui_logic: Dict[str, Any]            # Interaction semantics
    
@dataclass
class Intent:
    """Q_t - Current objective"""
    description: str                     # What to achieve
    step_name: str                       # Current workflow step
    context: Dict[str, Any]             # Additional metadata
```

**Key Functions**:
- `snapshot_current_state(project_path: Path) -> SoftwareState`
- `load_semantic_key(archetype: str) -> SemanticKey`
- `serialize_state(state: SoftwareState) -> bytes`
- `deserialize_state(data: bytes) -> SoftwareState`

**Dependencies**: None (foundation module)

---

### Module 2: `fingerprint.py` - Φ Canonical State

**Purpose**: Compute deterministic, semantic-equivalence hash

**Core Algorithm** (Section 5.2):
```
Φ(V) = Hash(
    AST_normalize(V.code_files),
    Dependency_graph(V.code_files),
    Failure_trace(execution_result)
)
```

**Implementation**:
```python
class CanonicalFingerprint:
    """Φ: V → Z (normalized representation space)"""
    
    def compute(self, state: SoftwareState, 
                execution_trace: Optional[ExecutionTrace] = None) -> str:
        """
        1. Normalize AST (remove comments, format, names)
        2. Build dependency graph (control + data flow)
        3. Encode failure trace (if present)
        4. Return SHA-256 hash
        """
        
    def _normalize_ast(self, code: str, language: str) -> AST:
        """Remove syntactic noise"""
        
    def _build_dep_graph(self, files: Dict[str, str]) -> DepGraph:
        """Extract functional dependencies"""
        
    def _encode_trace(self, trace: ExecutionTrace) -> bytes:
        """Canonicalize error signature"""
```

**Key Properties** (Appendix A.1):
- Deterministic: Same V always → same Φ(V)
- Invariant to syntax: Comments, whitespace, variable names ignored
- Failure-aware: Equivalent errors → equivalent fingerprints

**Dependencies**:
- `state.py` (SoftwareState)
- Python `ast` module
- Static analysis library (e.g., `tree-sitter`)

---

### Module 3: `failure_memory.py` - Global Failure Set (𝓕)

**Purpose**: Persistent, cross-project failure memory

**Core Structure** (Section 5.3):
```python
class GlobalFailureSet:
    """𝓕 = {Φ(V_i) | L(V_i) > 0}"""
    
    def __init__(self, db_path: Path):
        self.db = SQLiteDB(db_path)  # Persistent storage
        self.index = FAISSIndex()     # Fast similarity search
        
    def add_failure(self, fingerprint: str, 
                    metadata: Dict[str, Any]):
        """Add canonical failure to F"""
        
    def query_similar(self, fingerprint: str, 
                      threshold: float = 0.8) -> List[str]:
        """Find semantically similar failures"""
        
    def contains_equivalent(self, fingerprint: str) -> bool:
        """Check if equivalent failure exists"""
        
    def get_repulsion_weight(self, query_fingerprint: str) -> float:
        """Compute repulsion strength for given state"""
```

**Storage Schema**:
```sql
CREATE TABLE failures (
    fingerprint TEXT PRIMARY KEY,
    timestamp DATETIME,
    project_id TEXT,
    step_name TEXT,
    error_type TEXT,
    metadata JSON
);

CREATE INDEX idx_timestamp ON failures(timestamp);
CREATE INDEX idx_project ON failures(project_id);
```

**Key Requirements** (Appendix F.3):
- Persistent across projects
- Indexed for fast similarity lookup
- Append-only (preserve learning history)

**Dependencies**:
- `fingerprint.py` (CanonicalFingerprint)
- SQLite (persistence)
- FAISS or similar (approximate nearest neighbor)

---

### Module 4: `attention.py` - α(Q,K) + Repulsion

**Purpose**: Attention-based transformation selection with failure avoidance

**Core Equation** (Section 6.2):
```
α(Q,K) = Softmax(QK^T/√d_k) - λ∑(i∈F) Kernel(dist(K, K_i))
```

**Implementation**:
```python
class AttentionController:
    """Attention with failure repulsion"""
    
    def __init__(self, lambda_repulsion: float = 0.5):
        self.λ = lambda_repulsion
        
    def compute_attention(self, 
                         query: Intent,
                         keys: List[SemanticKey],
                         failure_set: GlobalFailureSet) -> np.ndarray:
        """
        Returns: Attention distribution over possible transformations
        
        Steps:
        1. Compute attraction: Softmax(QK^T/√d_k)
        2. Compute repulsion: λ∑Kernel(dist(K, K_i))
        3. Return: attraction - repulsion
        """
        
    def _attraction_term(self, Q: np.ndarray, K: np.ndarray) -> np.ndarray:
        """Standard dot-product attention"""
        d_k = K.shape[-1]
        scores = np.dot(Q, K.T) / np.sqrt(d_k)
        return softmax(scores)
        
    def _repulsion_term(self, keys: List[SemanticKey],
                       failure_set: GlobalFailureSet) -> np.ndarray:
        """Inhibit selection near known failures"""
        repulsion = np.zeros(len(keys))
        for i, key in enumerate(keys):
            fingerprint = self._key_to_fingerprint(key)
            repulsion[i] = failure_set.get_repulsion_weight(fingerprint)
        return self.λ * repulsion
        
    def _kernel(self, distance: float) -> float:
        """RBF kernel for smooth repulsion"""
        return np.exp(-distance**2 / (2 * self.sigma**2))
```

**Key Properties**:
- Monotonic exclusion of failure regions (Section 7.3)
- Smooth gradient for optimization
- Configurable λ for repulsion strength

**Dependencies**:
- `state.py` (Intent, SemanticKey)
- `failure_memory.py` (GlobalFailureSet)
- NumPy for vectorized operations

---

### Module 5: `validity.py` - Epistemic Grounding (K Invariants)

**Purpose**: Pre-execution correctness gate

**Core Function** (Section 5.6, 6.3):
```
1_Valid(K,V) ∈ {0,1}
```

**Implementation**:
```python
class ValidityGate:
    """Epistemic grounding - enforce K invariants"""
    
    def check_validity(self, semantic_key: SemanticKey,
                      state: SoftwareState) -> Tuple[bool, List[str]]:
        """
        Returns: (is_valid, list_of_violations)
        
        Checks:
        1. Domain schema consistency
        2. Business rule satisfaction
        3. Security constraint compliance
        4. UI logic coherence
        """
        violations = []
        
        violations.extend(self._check_domain_schema(semantic_key, state))
        violations.extend(self._check_business_rules(semantic_key, state))
        violations.extend(self._check_security(semantic_key, state))
        violations.extend(self._check_ui_logic(semantic_key, state))
        
        return (len(violations) == 0, violations)
        
    def _check_domain_schema(self, K: SemanticKey, V: SoftwareState) -> List[str]:
        """Validate entity relationships, foreign keys, etc."""
        
    def _check_business_rules(self, K: SemanticKey, V: SoftwareState) -> List[str]:
        """Validate invariants (e.g., Lead → Account → Deal lifecycle)"""
        
    def _check_security(self, K: SemanticKey, V: SoftwareState) -> List[str]:
        """Validate RBAC, auth, permissions"""
        
    def _check_ui_logic(self, K: SemanticKey, V: SoftwareState) -> List[str]:
        """Validate UI affordances match backend capabilities"""
```

**Invariant Examples** (CRM Case Study):
```python
CRM_INVARIANTS = {
    "lead_ownership": "Every Lead must have exactly one Owner",
    "deal_account_ref": "Every Deal must reference a valid Account",
    "rbac_enforcement": "Delete actions require admin role",
    "audit_logging": "All state mutations must be logged"
}
```

**Dependencies**:
- `state.py` (SemanticKey, SoftwareState)
- Static analysis for code inspection

---

### Module 6: `convergence.py` - Δα < ε Logic

**Purpose**: Detect stable equilibrium

**Core Condition** (Section 8):
```
Ω ⟺ (L=0) ∧ (Δα(Q,K) < ε)
```

**Implementation**:
```python
class ConvergenceDetector:
    """Monitor attention stability"""
    
    def __init__(self, epsilon: float = 0.01, window_size: int = 3):
        self.ε = epsilon
        self.window = window_size
        self.attention_history: Deque[np.ndarray] = deque(maxlen=window_size)
        
    def update(self, attention: np.ndarray):
        """Record new attention distribution"""
        self.attention_history.append(attention)
        
    def check_stability(self) -> Tuple[bool, float]:
        """
        Returns: (is_stable, max_delta)
        
        Stable if: max(|α_t - α_{t-1}|) < ε over window
        """
        if len(self.attention_history) < 2:
            return (False, float('inf'))
            
        deltas = []
        for i in range(1, len(self.attention_history)):
            delta = np.abs(self.attention_history[i] - self.attention_history[i-1])
            deltas.append(np.max(delta))
            
        max_delta = max(deltas)
        is_stable = max_delta < self.ε
        
        return (is_stable, max_delta)
        
    def check_convergence(self, loss: float) -> bool:
        """
        Ω = (L=0) ∧ (Δα < ε)
        """
        is_stable, _ = self.check_stability()
        return (loss == 0.0) and is_stable
```

**Key Properties** (Section 8.4, 8.5):
- Necessary: If Δα ≥ ε, system not done
- Sufficient: If L=0 ∧ Δα < ε, terminal equilibrium reached

**Dependencies**:
- NumPy for array operations

---

### Module 7: `mutation.py` - Architectural Pivots

**Purpose**: Escape local minima via structural mutation

**Core Concept** (Section 6.6, Appendix D.6):
```
V_{t+1} = Mutate(V_t)  when  Loss plateaus
```

**Implementation**:
```python
class MutationOperator:
    """Strategic architectural mutation"""
    
    def __init__(self, max_mutations_per_project: int = 3):
        self.max_mutations = max_mutations_per_project
        self.mutation_count = 0
        
    def should_mutate(self, loss_history: List[float],
                     stagnation_threshold: int = 3) -> bool:
        """
        Trigger mutation if loss plateaus for N iterations
        """
        if len(loss_history) < stagnation_threshold:
            return False
            
        recent = loss_history[-stagnation_threshold:]
        variance = np.var(recent)
        
        # Loss not decreasing
        is_stagnant = variance < 0.01 and recent[-1] > 0
        
        return is_stagnant and self.mutation_count < self.max_mutations
        
    def mutate(self, state: SoftwareState,
              strategy: str = "auto") -> SoftwareState:
        """
        Apply large-scale structural change
        
        Strategies:
        - database_model: Change ORM, schema structure
        - service_boundary: Alter API contracts
        - async_pattern: Switch sync ↔ async
        - framework: Replace core framework
        - ui_architecture: Change component structure
        """
        self.mutation_count += 1
        
        if strategy == "auto":
            strategy = self._select_strategy(state)
            
        return self._apply_mutation(state, strategy)
        
    def _select_strategy(self, state: SoftwareState) -> str:
        """Use heuristics to pick mutation type"""
        
    def _apply_mutation(self, state: SoftwareState, strategy: str) -> SoftwareState:
        """Execute architectural transformation"""
```

**Mutation Examples** (Appendix C.5):
- Sync → Async audit logging
- Monolithic → Microservice split
- REST → GraphQL
- SQL → NoSQL

**Dependencies**:
- `state.py` (SoftwareState)
- LLM adapter for code transformation

---

### Module 8: `governor.py` - Main Control Loop (Ω)

**Purpose**: ArborMind's central controller

**Core Algorithm** (Appendix B.1):
```python
class ArborMindGovernor:
    """Main control loop implementing Ω"""
    
    def __init__(self, project_id: str, intent: Intent,
                semantic_key: SemanticKey):
        self.project_id = project_id
        self.intent = intent
        self.semantic_key = semantic_key
        
        # Core components
        self.fingerprinter = CanonicalFingerprint()
        self.failure_set = GlobalFailureSet(DB_PATH)
        self.attention = AttentionController(lambda_repulsion=0.5)
        self.validity_gate = ValidityGate()
        self.convergence = ConvergenceDetector(epsilon=0.01)
        self.mutator = MutationOperator()
        
        # State tracking
        self.current_state: SoftwareState = None
        self.loss_history: List[float] = []
        
    async def run(self, initial_state: SoftwareState) -> SoftwareState:
        """
        Main control loop (Appendix B.1)
        
        while True:
            1. Validity gate check
            2. Compute attention
            3. Check convergence (Ω)
            4. Apply transformation
            5. Execute oracle
            6. Heal or mutate
        """
        V = initial_state
        α_prev = None
        
        while True:
            # Step 1: Validity gate
            is_valid, violations = self.validity_gate.check_validity(
                self.semantic_key, V
            )
            
            if not is_valid:
                fingerprint = self.fingerprinter.compute(V)
                self.failure_set.add_failure(fingerprint, {
                    "violations": violations,
                    "step": "validity_gate"
                })
                V = await self.mutator.mutate(V)
                continue
                
            # Step 2: Compute attention
            α = self.attention.compute_attention(
                self.intent,
                self._get_transformation_keys(V),
                self.failure_set
            )
            
            # Step 3: Check convergence Ω
            L = await self._execute_oracle(V)
            self.convergence.update(α)
            
            if self.convergence.check_convergence(L):
                logger.info(f"Ω reached: L={L}, Δα < ε")
                await self._deploy(V)
                return V
                
            # Step 4: Apply transformation
            V_next = await self._apply_transformation(V, α)
            
            # Step 5: Execute oracle
            L_next = await self._execute_oracle(V_next)
            
            # Step 6: Heal or mutate
            if L_next == 0:
                V = V_next
            else:
                fingerprint = self.fingerprinter.compute(V_next)
                self.failure_set.add_failure(fingerprint, {
                    "loss": L_next,
                    "step": self.intent.step_name
                })
                
                self.loss_history.append(L_next)
                
                if self.mutator.should_mutate(self.loss_history):
                    V = await self.mutator.mutate(V)
                else:
                    V = await self._heal(V_next, L_next)
                    
            α_prev = α
            
    async def _execute_oracle(self, state: SoftwareState) -> float:
        """
        Multimodal execution oracle (Section 6.4)
        
        L = E_static + E_logical + E_visual
        """
        from app.arbormind.adapters.oracle import ExecutionOracle
        oracle = ExecutionOracle()
        return await oracle.evaluate(state)
        
    async def _heal(self, state: SoftwareState, loss: float) -> SoftwareState:
        """
        Gradient-based healing (Section 6.5)
        
        V_{t+1} = V_t - η∇_V L
        """
        from app.arbormind.adapters.agents import AgentAdapter
        adapter = AgentAdapter()
        return await adapter.heal(state, loss, learning_rate=0.1)
        
    async def _apply_transformation(self, state: SoftwareState,
                                   attention: np.ndarray) -> SoftwareState:
        """Apply attention-selected transformation"""
        
    async def _deploy(self, state: SoftwareState):
        """Freeze and deploy converged state"""
```

**Key Properties**:
- Deterministic given V_0, K, F
- Guaranteed termination (Theorem A.2)
- No infinite loops (Theorem A.1)

**Dependencies**:
- All other ArborMind modules
- Adapter modules

---

## Module 9-11: Adapters (Integration Layer)

### 9.1 `adapters/orchestrator.py` - FAST V2 Integration

**Purpose**: Wire ArborMind Governor into FAST V2 orchestrator

**Implementation**:
```python
class FASTOrchestratorAdapter:
    """Adapt ArborMind to FAST V2 orchestrator"""
    
    def wrap_handler(self, handler: Callable,
                    step_name: str) -> Callable:
        """
        Wrap FAST V2 handler with ArborMind governance
        
        Before handler:
        - Extract semantic key for step
        - Initialize ArborMind Governor
        
        After handler:
        - Record outcome in failure set
        - Check convergence
        """
        
    async def augment_orchestrator(self, orchestrator: FASTOrchestratorV2):
        """
        Inject ArborMind control loop into orchestrator
        
        Hooks:
        - Pre-step: Validity gate
        - Post-step: Oracle execution
        - On-failure: Healing or mutation
        - On-convergence: Early termination
        """
```

**Integration Points**:
- `FASTOrchestratorV2.run()` main loop
- Handler execution wrapping
- Checkpoint/resume integration

---

### 9.2 `adapters/agents.py` - Derek/Victoria/Luna Integration

**Purpose**: Use existing agents as actuators

**Implementation**:
```python
class AgentAdapter:
    """Adapt existing agents as ArborMind actuators"""
    
    async def heal(self, state: SoftwareState, loss: float,
                  learning_rate: float) -> SoftwareState:
        """
        Use agents to heal failures
        
        Maps loss → agent prompt:
        - Static errors → Derek (code fixes)
        - Logical errors → Victoria (architecture adjustments)
        - Visual errors → Luna (UI fixes)
        """
        from app.agents.sub_agents import marcus_call_sub_agent
        
        # Determine which agent to use
        agent_name = self._select_agent_for_loss_type(loss)
        
        # Generate healing prompt
        prompt = self._build_healing_prompt(state, loss, learning_rate)
        
        # Call agent (actuator)
        result = await marcus_call_sub_agent(
            agent_name=agent_name,
            user_request=prompt,
            project_path=state.project_path
        )
        
        # Apply fixes to state
        return self._apply_fixes(state, result)
```

**Key Principle** (Section 9.3):
- Agents do NOT reason independently
- Agents do NOT decide correctness
- Agents are bounded actuators executing transformations

---

### 9.3 `adapters/oracle.py` - Validation + Sandbox Integration

**Purpose**: Multimodal execution oracle

**Implementation**:
```python
class ExecutionOracle:
    """
    Multimodal correctness evaluation (Section 6.4)
    
    L = E_static + E_logical + E_visual
    """
    
    async def evaluate(self, state: SoftwareState) -> float:
        """
        Returns: Execution loss ∈ [0, ∞)
        
        0 means all checks pass
        """
        static_loss = await self._static_analysis(state)
        logical_loss = await self._logical_validation(state)
        visual_loss = await self._visual_testing(state)
        
        # Weighted sum
        total_loss = (
            0.3 * static_loss +
            0.4 * logical_loss +
            0.3 * visual_loss
        )
        
        return total_loss
        
    async def _static_analysis(self, state: SoftwareState) -> float:
        """
        Syntax, linting, type checks
        
        Uses existing validation modules
        """
        from app.validation import syntax_validator, static_validator
        
    async def _logical_validation(self, state: SoftwareState) -> float:
        """
        Domain invariant checks
        
        Uses validity gate + business rule verification
        """
        from app.arbormind.validity import ValidityGate
        
    async def _visual_testing(self, state: SoftwareState) -> float:
        """
        UI rendering, interaction tests
        
        Uses sandbox for Playwright execution
        """
        from app.sandbox.sandbox_manager import SandboxManager
```

**Integration Points**:
- `app.validation.*` for static checks
- `app.sandbox.*` for runtime execution
- `app.supervision.*` for Marcus review

---

## Data Structures

### Core Types (to be added to `app/core/types.py`)

```python
@dataclass
class ExecutionTrace:
    """Trace of execution for fingerprinting"""
    error_type: str
    stack_trace: str
    failed_assertion: Optional[str]
    visual_diff: Optional[bytes]
    timestamp: datetime
    
@dataclass
class TransformationKey:
    """Semantic key for a transformation option"""
    description: str
    code_change_type: str  # "refactor", "feature", "fix"
    affected_modules: List[str]
    embedding: np.ndarray  # For attention computation
    
@dataclass
class ControlState:
    """Complete ArborMind control state"""
    software_state: SoftwareState
    semantic_key: SemanticKey
    intent: Intent
    attention_distribution: np.ndarray
    current_loss: float
    iteration: int
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal**: Core data structures and primitives

- [ ] Implement `state.py`
  - SoftwareState, SemanticKey, Intent classes
  - Snapshot/serialization functions
- [ ] Implement `fingerprint.py`
  - AST normalization
  - Dependency graph extraction
  - Hash computation
- [ ] Implement `failure_memory.py`
  - SQLite schema
  - FAISS index setup
  - Add/query functions
- [ ] Unit tests for all foundation modules

**Deliverable**: Foundation modules with >80% test coverage

---

### Phase 2: Control Mechanisms (Week 2)
**Goal**: Attention, validity, convergence

- [ ] Implement `attention.py`
  - Attraction term (softmax attention)
  - Repulsion term (kernel-based)
  - Combined alpha computation
- [ ] Implement `validity.py`
  - Domain schema checks
  - Business rule validation
  - Security constraint enforcement
- [ ] Implement `convergence.py`
  - Attention stability tracking
  - Ω condition check
- [ ] Integration tests for control flow

**Deliverable**: Working attention + validity + convergence pipeline

---

### Phase 3: Mutation & Healing (Week 3)
**Goal**: Recovery mechanisms

- [ ] Implement `mutation.py`
  - Stagnation detection
  - Mutation strategy selection
  - Architectural transformations
- [ ] Implement healing logic in `governor.py`
  - Gradient-based correction
  - LLM-based fix generation
- [ ] Integration with existing agents
- [ ] End-to-end healing tests

**Deliverable**: Autonomous error correction working

---

### Phase 4: Governor & Control Loop (Week 4)
**Goal**: Main control loop

- [ ] Implement `governor.py`
  - Main while loop (Appendix B.1)
  - State transition logic
  - Convergence termination
- [ ] Implement execution oracle
  - Multimodal loss computation
  - Integration with validation/sandbox
- [ ] Integration tests with mock states

**Deliverable**: Governor can complete simple workflows

---

### Phase 5: FAST V2 Integration (Week 5)
**Goal**: Wire into existing orchestrator

- [ ] Implement `adapters/orchestrator.py`
  - Handler wrapping
  - Hook injection into FAST V2
  - Checkpoint integration
- [ ] Implement `adapters/agents.py`
  - Agent selection logic
  - Healing prompt generation
- [ ] Implement `adapters/oracle.py`
  - Static/logical/visual validation
  - Loss aggregation
- [ ] Integration tests with real FAST V2 workflows

**Deliverable**: ArborMind governing FAST V2 on real projects

---

### Phase 6: Optimization & Production (Week 6)
**Goal**: Performance and reliability

- [ ] Optimize fingerprint computation
  - AST caching
  - Incremental dependency graphs
- [ ] Optimize failure set queries
  - FAISS tuning
  - Batch similarity search
- [ ] Add comprehensive logging
  - State transitions
  - Mutation events
  - Convergence checks
- [ ] Production deployment prep
  - Error handling
  - Resource limits
  - Monitoring hooks

**Deliverable**: Production-ready ArborMind

---

## Testing Strategy

### Unit Tests
Each module must have:
- **Happy path**: Normal operation
- **Edge cases**: Empty inputs, extreme values
- **Error handling**: Invalid states, computation failures

### Integration Tests
- **Control flow**: Attention → Validity → Execution → Healing
- **Failure memory**: Add failure → Query → Repulsion works
- **Convergence**: Multiple iterations → Ω reached

### End-to-End Tests
- **Simple CRM**: ArborMind builds working CRM autonomously
- **Failure repetition**: Same canonical failure not repeated
- **Mutation**: Stagnation triggers architectural change
- **Termination**: Ω condition correctly stops execution

### Performance Tests
- **Fingerprint speed**: < 100ms per state
- **Attention compute**: < 500ms per iteration
- **Failure query**: < 50ms for similarity search
- **Overall**: Converge within 20 minutes (CRM case study)

---

## Success Criteria

ArborMind implementation is complete when:

1. ✅ **Completion**: Autonomously builds working CRM (Section 10)
2. ✅ **Correctness**: Multimodal oracle passes (L=0)
3. ✅ **Autonomy**: No human intervention required
4. ✅ **Non-Repetition**: Failure set prevents canonical failures
5. ✅ **Determinism**: Same inputs → same outputs
6. ✅ **Convergence**: Ω condition mathematically satisfied
7. ✅ **Performance**: Sub-20-minute time-to-production

---

## References

- **Main Research**: `Backend/ArborMind/ArborMind Research.txt`
- **Pseudocode**: Appendix B (lines 659-758)
- **Case Study**: Appendix C (lines 769-859)
- **Ablations**: Appendix D (lines 879-980)
- **Implementation Notes**: Appendix F (lines 1058-1134)

---

## Next Steps

1. Review this plan with team
2. Set up development environment
3. Begin Phase 1 implementation
4. Establish CI/CD for automated testing
5. Weekly progress reviews against milestones

**Estimated Timeline**: 6 weeks to production-ready ArborMind
