# Task List — GenxAI Studio V4 Clean-Room Refactor

## V3 Cleanup Tasks (DELETE ENTIRELY)

- [ ] Delete Legacy Orchestration
  - [ ] Delete `Backend/app/orchestration/fast_orchestrator.py`
  - [ ] Delete legacy step, pipeline, and phase execution loops
  - [ ] Delete self-healing manager and retry-based healing loop files
  - [ ] Remove old DB materializer bypass overrides

- [ ] Delete Legacy Agent Systems
  - [ ] Delete anthropomorphic agent prompt configurations
  - [ ] Delete phase-based and retry-centric agent files
  - [ ] Remove "fix this code" interactive prompt chains

- [ ] Delete Legacy Abstractions
  - [ ] Delete `Backend/app/orchestration/frontend_mock.py`
  - [ ] Delete `Backend/app/orchestration/backend_models.py`
  - [ ] Delete `Backend/app/orchestration/backend_routers.py`
  - [ ] Delete old HDAP recovery and malformed marker correction logic
  - [ ] Remove legacy planners and phase supervision files
  - [ ] Delete unused handlers and legacy patchers

---

## Safe Implementation Roadmap (Gated Build Order)

### Stage 1 — Freeze Runtime

- [ ] Substrate Management Setup
  - [ ] Implement deterministic stable execution substrate (`substrate_manager.py`)
  - [ ] Lock framework configurations from cognitive mutation

- [ ] Core Execution Leases
  - [ ] Implement `leases.py` protecting execution blocks and preventing split-brain states
  - [ ] Create Beanie persistence schemas for sessions, leases, and transactions in `runtime_models.py`
  - [ ] Wire MongoDB initialization updates in `db/__init__.py`

- [ ] Projection Snapshots & Rollback
  - [ ] Implement `projection_snapshots.py` creating atomic topology, AST, filesystem, and runtime snapshots before every projection cycle
  - [ ] Implement `transaction_engine.py` coordinating transaction boundaries, commits, and transaction hashes
  - [ ] Build `workspace_snapshots.py` for rapid workspace snapshots and recoveries

- [ ] Execution Contracts
  - [ ] Implement `execution_contracts.py` defining mutation legality, topology scope, oracle requirements, and projection boundaries

- [ ] Drift Detection
  - [ ] Implement `drift_detection.py` to trigger invalidations, reconstruction, or rollbacks on manual edits

- [ ] Execution Kernel
  - [ ] Implement `execution_kernel.py` orchestrating AST projection, sandboxing, leases, rollbacks, and commits

---

### Stage 2 — Canonical Topology

- [ ] IntentField Setup
  - [ ] Implement boundary-based `directive.py` defining semantic invariants, UX targets, and constraints (no rigid blueprints)

- [ ] Canonical Topology Engine
  - [ ] Implement `project_graph.py` defining the Master Topology DAG as canonical state
  - [ ] Create `node_types.py` classifying graph nodes (`API_NODE`, `UI_NODE`, etc.)
  - [ ] Implement `topology_compiler.py` converting compiled `IntentField` boundaries, UX ontologies, data models, routes, and workflow rules into canonical topology
  - [ ] Implement topology reconstruction from AST projections with filesystem reconciliation fallback in `topology_builder.py`
  - [ ] Implement `structural_diff.py` conducting structural comparisons (APIs, schemas, routes, components, import boundaries, topology edges)
  - [ ] Implement `topology_validator.py` validating import paths, cyclic boundaries, and routing schemas
  - [ ] Implement `topology_version_manager.py` managing graph snapshots, diff lineage, and branch merges
  - [ ] Implement topology integrity hash generation tasks to prevent structural corruption

---

### Stage 3 — AST Pipeline

- [ ] AST Engine
  - [ ] Implement `ast_generator.py` generating AST structures from topology nodes
  - [ ] Implement `ast_mutator.py` executing controlled AST transformations
  - [ ] Implement `ast_merger.py` merging AST structures into existing files safely
  - [ ] Implement `ast_projector.py` writing AST configurations directly to disk
  - [ ] Implement `ast_validator.py` verifying syntax and structural correctness before writing
  - [ ] Implement AST projection integrity hash generation and verification tasks

- [ ] Materialization Projection Layers
  - [ ] Refactor `materializers.py` into topology projection layers

---

### Stage 4 — Oracle Layer

- [ ] Modular Oracle Hierarchy
  - [ ] Define modular Oracle interface structures in `base.py`
  - [ ] Implement `syntax_oracle.py` conducting AST syntax checks (HARD)
  - [ ] Implement `topology_oracle.py` verifying graph imports and dependencies (HARD)
  - [ ] Implement `behavioral_oracle.py` checking business routes and workflows (HARD)
  - [ ] Implement `runtime_oracle.py` conducting unit and E2E test runs (HARD)
  - [ ] Implement `visual_oracle.py` conducting soft-structural validations (DOM integrity, layout hierarchy, responsive containers, Tailwind classes)
  - [ ] Implement `semantic_oracle.py` as an advisory-only soft oracle to detect drift (never approves commits or overrides hard failures)
  - [ ] Implement `convergence_oracle.py` measuring stability thresholds (SOFT)
  - [ ] Create `evidence_registry.py` tracking traces, screenshots, and logs to verify claim keys

---

### Stage 5 — Runtime Synchronization

- [ ] Synchronization & Recovery
  - [ ] Implement `runtime_projection_validator.py` continuously verifying filesystem congruence against active AST projections
  - [ ] Implement `reality_sync.py` executing DB/Filesystem/Runtime validation checks and managing Branch Invalidation
  - [ ] Implement non-cognitive `reconstruction.py` (Disaster Recovery topology reconstruction from AST and logs)

- [ ] Transaction & Projection Hashes
  - [ ] Generate structural integrity hashes across topology, AST projections, and transaction states before commits

---

### Stage 6 — Minimal Cognition

- [ ] Bounded Faculty System
  - [ ] Refactor `sub_agents.py` simplifying Victoria, Derek, Luna, Marcus, Reggie to pure cognitive faculties
    - [ ] Prevent faculties from generating structural architecture directly
    - [ ] Restrict faculties to bounded implementation synthesis within topology and AST constraints
    - [ ] Force Marcus to purely emit governance signals with zero direct execution authority
  - [ ] Implement `arbor_runtime.py` as the Cognitive Branch Controller coordinating event-driven cycles
    - [ ] Preserve deterministic realization and validation execution order
    - [ ] Restrict non-linearity to cognition and branch exploration only

- [ ] Cognition & Constraint Engine
  - [ ] Create `arbor_core.py` governing branch exploration, arbitration, and mutation paths (restricted to topology mutation space)
  - [ ] Implement `branch.py` containing `BranchState` tracking metrics (topology, oracle history, entropy, failure proximity)
  - [ ] Implement `constraint_engine.py` validating mutations against hard rules and forbidden topology states (Tiers 1-5 Mutation Classes)
  - [ ] Implement `patch_ir.py` defining target topology, AST target, mutation type, and safety constraints
  - [ ] Create `attention_router.py` dynamically allocating cognitive resources based on stability, cost, and entropy
  - [ ] Implement `convergence_engine.py` evaluating topological metrics and pruning criteria
  - [ ] Implement `branch_budget_manager.py` merging and pruning active branch states
  - [ ] Create `branch_lineage.py` mapping cognitive genealogy trees
  - [ ] Create `restructuring_engine.py` coordinating recovery when oracle failures block branches

- [ ] Mutation Engine
  - [ ] Implement `mutation_engine.py` coordinating event-driven, convergence-weighted transitions (triggered by entropy, stagnation, or oracles)
  - [ ] Implement mutation cost functions governed by weighted branch optimizations

- [ ] Failure Memory
  - [ ] Implement `repulsion_engine.py` and `failure_geometry.py` mapping logs, exceptions, AST, and topologies to NumPy embeddings
  - [ ] Integrate SQLite local storage in `vector_store.py` for failure similarity scoring

---

## V4.2 Experimental Systems (DEFERRED)

- [ ] Deferred Learning Systems
  - [ ] Implement `runtime_learning.py` mapping feedback profiles
  - [ ] Implement `cognitive_compression.py` compressing mutation paths into reusable heuristics
  - [ ] Implement `semantic_compression.py` mapping topological structural motifs

---

## Verification & Governance Validation Tests

- [ ] Canonical Topology Tests
  - [ ] Verify topology graph remains canonical during all execution stages
  - [ ] Verify filesystem projections cannot mutate topology directly

- [ ] Structural Governance Tests
  - [ ] Write tests ensuring LLMs cannot create topology structures directly
  - [ ] Write tests ensuring all file outputs originate from AST projections
  - [ ] Write tests validating topology as canonical source of truth
  - [ ] Verify emergence boundaries lock execution kernel, oracle authority, and transaction safety from cognitive mutation

- [ ] Projection Synchronization Tests
  - [ ] Write synchronization divergence tests for:
    - [ ] DB vs filesystem
    - [ ] topology vs runtime
    - [ ] topology vs AST
    - [ ] runtime vs deployment

- [ ] Split-Brain Recovery Tests
  - [ ] Test system behavior during hot reload mid-transaction
  - [ ] Test recovery during interrupted AST projection
  - [ ] Test behavior on stale topology metadata and stale DB records
  - [ ] Test system recovery for orphan leases, partial rollbacks, and workspace wipes

- [ ] Hard vs Soft Oracle Tests
  - [ ] Verify soft oracles cannot override hard oracle failures
  - [ ] Verify Semantic Oracle signals function purely as advisory drift metrics

- [ ] Core Logic & Concurrency Verification
  - [ ] Write unit tests for the Transactional State Machine (`test_state_machine.py`)
  - [ ] Write concurrency tests for Lease Locks (`test_leases.py`)
  - [ ] Conduct manual React UI/Vite rendering checks and Beanie database collection verifications
