<div align="center">

<br />
<br />

# 🧠 GenCode Studio — Backend

### **The AI Engine That Powers Intelligent Code Generation**

<br />

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.122+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Beanie-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Docker](https://img.shields.io/badge/Docker-Sandbox-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![ArborMind](https://img.shields.io/badge/ArborMind-Integrating-6B21A8?style=for-the-badge&logo=leaflet&logoColor=white)](#-arbormind--the-next-generation-control-layer)

<br />

The **Backend** is the intelligence core — a research-grade orchestration system that coordinates AI agents, enforces failure taxonomy, learns from every run, and produces production-ready code autonomously.

<br />

> *Receives a prompt → Orchestrates 12 intelligent steps → Delivers tested, deployable code*

<br />

[⚡ Pipeline](#-the-fast-v2-pipeline) · [🌳 ArborMind](#-arbormind--the-next-generation-control-layer) · [🛡️ Reliability](#-evidence-based-reliability) · [🚀 Quick Start](#-quick-start) · [📁 Structure](#-directory-structure) · [📖 API](#-api-reference)

<br />

---

</div>

<br />

## ⚡ Core Capabilities

<div align="center">

### ⚙️ FAST V2 Orchestrator
The intelligent workflow engine: **12 atomic steps** with dependency barriers · **Budget tracking** per step · **Checkpointing** for resume · **Cross-step context** sharing

### 🌳 ArborMind Governor *(In Integration)*
Control-theoretic AGI layer: **Attention-based routing** with failure repulsion · **Global failure memory** across projects · **Autonomous architectural mutation** · **Formal convergence guarantees**

### 🛡️ Evidence-Based Reliability
Strict failure isolation: **Environment vs Cognitive** failure separation · **Selective retries** for infra only · **Quarantine** for logic failures · **One-Shot Policy** for causal steps

### 🐳 Docker Sandbox
Full isolated testing: **Containerised pytest** runs · **Playwright E2E** testing · **MongoDB** test instances · **Complete isolation** per project

</div>

<br />

---

<br />

## ⚡ The FAST V2 Pipeline

The FAST V2 Orchestrator executes a carefully sequenced 12-step pipeline across 4 phases. Each step is **atomic**, has **explicit dependencies**, and runs with a **token budget cap**.

### 🔍 Phase 1 — Analysis
> **Marcus** → `analysis` — Extract entities, classify archetype, infer data model
> **Victoria** → `architecture` — Design system, create schemas, define API surface

### 🎨 Phase 2 — Frontend
> **Derek** → `frontend_mock` — Generate full React UI with mock data
> **Marcus** → `screenshot_verify` — Visual QA review of rendered UI
> **Marcus** → `contracts` — Define OpenAPI specifications

### ⚙️ Phase 3 — Backend
> **Derek** → `backend_models` — Generate Beanie/MongoDB document models
> **Derek** → `backend_impl` — Create FastAPI routers and business logic
> **Script** → `system_integration` — Wire `main.py`, `requirements.txt`, CORS, auth

### ✅ Phase 4 — Testing & Deploy
> **Derek** → `testing_backend` — Generate and run pytest in Docker
> **Derek** → `frontend_integration` — Connect React UI to real API endpoints
> **Luna** → `testing_frontend` — Playwright E2E tests in headless browser
> **Marcus** → `preview_final` — Final review and deployment readiness

**Step Execution Rules:**
- **Causal steps** (code generation): One-Shot — no automatic retries
- **Evidence steps** (docker tests, network): Selective retry on `ENVIRONMENT_FAILURE`
- **Budget**: Each step has a hard token cap enforced by `budget_manager.py`
- **Checkpointing**: Workflow can resume from any completed step after a restart

<br />

---

<br />

## 🌳 ArborMind — The Next-Generation Control Layer

> **Status: 🔄 Active Integration** — Phase 1–3 modules implemented, adapter layer connecting to FAST V2

ArborMind is a **control-theoretic orchestration engine** that transforms FAST V2 from a linear pipeline into a **governed, self-healing, learning system**. It implements the mathematical framework from the ArborMind research whitepaper.

### The Core Idea

Instead of fixed retry logic or heuristic healing, ArborMind uses a **formal control loop** with convergence guarantees:

```
State: S_t = (V_t, K_t, Q_t, F)

  V_t  — Executable software artifact (code, config, schema, assets)
  K_t  — Semantic key (domain rules, invariants, business logic)
  Q_t  — Current intent / objective
  F    — Global Failure Set (persistent across ALL projects)

Control Equation:
  α(Q,K) = Softmax(QKᵀ/√d_k) − λΣ(i∈F) Kernel(dist(K, Kᵢ))
            ↑ Attraction to good strategies   ↑ Repulsion from known failures

Convergence (Ω):
  Ω ≡ (L=0) ∧ (α(Q,K) < ε)     → Deploy & Stop
```

### Design Principles

| Principle | Description |
|:----------|:------------|
| **Strict Authority Separation** | LLM *actuates*, Governor *controls* — LLM never decides termination or correctness |
| **Deterministic Execution** | Same `V₀`, `K`, `F` → same execution path, every time |
| **Global Memory** | `F` persists across projects, servers, and restarts via SQLite |
| **Multimodal Truth** | Oracle evaluates: Static analysis + Logical validation + Visual verification |
| **Hard Stop (Ω)** | Formal convergence condition — no infinite loops (proven by Theorem A.1) |

### ArborMind Module Map

```
app/arbormind/
│
├── phase_1/                          # Foundation
│   ├── state.py                      # SoftwareState (V_t), SemanticKey (K_t), Intent (Q_t)
│   ├── canonical_fingerprint.py      # φ: V → ℤ  (AST-normalised, failure-aware hash)
│   ├── failure_memory.py             # GlobalFailureSet (F) — SQLite + similarity index
│   └── state_gate.py                 # Validity gate: 1_Valid(K,V) ∈ {0,1}
│
├── phase_2/                          # Intelligence
│   ├── attention_bias.py             # Repulsion bias computation
│   ├── cognitive_directive.py        # Directive management
│   ├── failure_taxonomy.py           # Failure classification taxonomy
│   └── mutation_authority.py        # Mutation decision authority
│
├── phase_3/                          # Control Loop
│   ├── governor.py                   # ArborMindGovernor — main control loop (Ω)
│   ├── attention.py                  # α(Q,K): attention + repulsion computation
│   ├── convergence.py                # Convergence detector
│   ├── convergence_ledger.py         # Loss history tracking
│   ├── circularity_monitor.py        # Loop detection
│   ├── divergence_controller.py      # Divergence handling
│   ├── mutation_law.py               # Mutation strategy selection
│   └── validity.py                   # Epistemic grounding gate
│
├── adapters/                         # Integration with FAST V2
│   ├── orchestrator.py               # Main FAST V2 ↔ ArborMind bridge (20KB)
│   ├── oracle.py                     # Multimodal execution oracle
│   ├── agents.py                     # Agent action adapter (heal/mutate)
│   ├── execution_adapter.py          # Step execution bridge
│   ├── lineage_tracker.py            # Execution lineage
│   ├── tool_binding.py               # Tool system binding
│   └── continuation_controller.py   # Continuation flow control
│
└── persistence/                      # Cross-project Memory
    ├── interfaces/                   # Abstract store contracts
    │   ├── failure_store.py          # IFailureStore
    │   ├── directive_store.py        # IDirectiveStore
    │   └── lineage_store.py          # ILineageStore
    └── backends/sqlite/              # Concrete SQLite implementation
        ├── schema.sql                # DB schema (failures, directives, lineage)
        ├── sqlite_failure_store.py   # Persistent failure memory
        ├── sqlite_directive_store.py # Directive persistence
        └── sqlite_lineage_store.py   # Lineage persistence
```

### What Changes When ArborMind Is Live

| Current (FAST V2) | With ArborMind |
|:------------------|:---------------|
| Fixed retry count | Governor decides retry via attention + loss |
| Healing = re-prompt | Healing = gradient-guided correction `V_{t+1} = V_t − η∇_V L` |
| Failures forgotten after session | Failures stored in `F` forever, repel future attempts |
| Sequential pipeline | Adaptive loop with convergence condition |
| No mutation | Autonomous framework/architecture mutation if stuck |

> See [`ARBORMIND_IMPLEMENTATION_PLAN.md`](ARBORMIND_IMPLEMENTATION_PLAN.md) for the full phase-by-phase implementation guide and [`ARBORMIND_CONFLICTS.md`](ARBORMIND_CONFLICTS.md) for resolved FAST V2 authority conflicts.

<br />

---

<br />

## 🛡️ Evidence-Based Reliability

<div align="center">
<sub><i>Strict failure taxonomy with explicit containment strategies</i></sub>
</div>

<br />

The system enforces a strict **One-Shot Policy** for all causal steps, relying on precise failure classification rather than infinite retry loops:

<table>
<tr>
<td width="50%">

### 📊 Outcome Taxonomy

| Type | Logic | Handling |
|:-----|:------|:---------|
| **SUCCESS** | Steps verify OK | Proceed |
| **ENVIRONMENT_FAILURE** | Infra/Network/Docker | **Retry** (Evidence steps only) |
| **COGNITIVE_FAILURE** | Agents/Tests/Reasoning | **Isolate** (No auto-healing) |
| **HARD_FAILURE** | Logical Impossibility | **Stop** Workflow |

</td>
<td width="50%">

### 🔒 Isolation Strategy

```
Step Failure
     ↓
Failure Classifier
     ↓
┌────────────────────┐
│  INFRA  │ COGNITIVE │
│ (Retry) │ (Isolate) │
└────┬────┴─────┬─────┘
     ↓          ↓
  Continue   Quarantine
                ↓
           Human Review
```

</td>
</tr>
</table>

<br />

**Core Reliability Files:**

| File | Purpose |
|:-----|:--------|
| `core/step_outcome.py` | Taxonomy definitions (Success, Env, Cognitive, Hard) |
| `core/failure_boundary.py` | Runtime enforcement decorator |
| `core/guard.py` | Orchestration safety guard |
| `core/step_invariants.py` | Per-step invariant enforcement |
| `orchestration/budget_manager.py` | Token budget — hard cap per step |
| `orchestration/checkpoint.py` | Progress persistence — resume from any step |

<br />

---

<br />

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │
│   │   REST API   │   │  WebSocket   │   │    Health    │           │
│   │   /api/*     │   │  /ws/{id}    │   │   /health    │           │
│   └──────┬───────┘   └──────┬───────┘   └──────────────┘           │
│          │                   │                                        │
│          ▼                   ▼                                        │
│   ┌───────────────────────────────────────────────────────────┐     │
│   │                   FAST V2 ORCHESTRATOR                     │     │
│   │      12 Steps · Dependencies · Budget · Checkpoints        │     │
│   └────────────────────────┬──────────────────────────────────┘     │
│                             │                                         │
│          ┌──────────────────┼──────────────────┐                    │
│          ▼                  ▼                   ▼                    │
│   ┌─────────────┐   ┌─────────────┐   ┌──────────────┐            │
│   │   Handlers  │   │   Agents    │   │  Supervision  │            │
│   │ 12 Steps    │   │  M/V/D/L/R  │   │  Quality Gate │            │
│   └──────┬──────┘   └──────┬──────┘   └──────────────┘            │
│          │                  │                                         │
│          ▼                  ▼                                         │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    LLM PROVIDERS                             │   │
│   │         Gemini (default) · OpenAI · Anthropic · Ollama      │   │
│   └──────────────────────────────────────────────────────────────┘  │
│                             │                                         │
│          ┌──────────────────┼──────────────────┐                    │
│          ▼                  ▼                   ▼                    │
│   ┌─────────────┐   ┌─────────────┐   ┌──────────────┐            │
│   │ Validation  │   │ Persistence │   │   Tracking   │            │
│   │ AST+Safety  │   │ File Writer │   │  Prometheus  │            │
│   └─────────────┘   └─────────────┘   └──────────────┘            │
│                             │                                         │
│                             ▼                                         │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    DOCKER SANDBOX                            │   │
│   │          pytest · Playwright E2E · MongoDB · Preview         │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                             │                                         │
│         ┌───────────────────┘  (ArborMind Integration)               │
│         ▼                                                             │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │               🌳 ARBORMIND GOVERNOR (In Integration)         │   │
│   │    Attention Router · Failure Memory · Convergence Loop      │   │
│   │    SQLite Persistence · Multimodal Oracle · Mutation Engine  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

<br />

---

<br />

## 📁 Directory Structure

```
Backend/
├── app/
│   ├── main.py                          # FastAPI entry point & lifespan
│   │
│   ├── 🌐 api/                          # REST Endpoints (9 files)
│   │   ├── workspace.py                 # Generation API — POST /generate
│   │   ├── projects.py                  # Project CRUD
│   │   ├── sandbox.py                   # Docker management
│   │   ├── agents.py                    # Agent status
│   │   ├── deployment.py                # Deployment API
│   │   ├── providers.py                 # LLM provider config
│   │   ├── tracking.py                  # Telemetry API
│   │   └── health.py                    # Health check
│   │
│   ├── ⚙️ orchestration/                # FAST V2 Core (14 files)
│   │   ├── fast_orchestrator.py         # Main orchestrator (~823 lines)
│   │   ├── budget_manager.py            # Token budget tracking
│   │   ├── checkpoint.py                # Progress save/resume
│   │   ├── task_graph.py                # Step dependency graph
│   │   ├── context.py                   # Cross-step execution context
│   │   ├── router_utils.py              # Attention routing utilities
│   │   ├── state.py                     # Workflow state manager
│   │   └── ...                          # (+6 supporting modules)
│   │
│   ├── 🤖 handlers/                     # Step Handlers (12 files)
│   │   ├── architecture.py              # Victoria: system design
│   │   ├── backend_models.py            # Derek: Beanie models
│   │   ├── backend_routers.py           # Derek: FastAPI routers
│   │   ├── frontend_mock.py             # Derek: React UI
│   │   ├── testing_backend.py           # pytest in Docker
│   │   ├── testing_frontend.py          # Luna: Playwright E2E
│   │   ├── system_integration.py        # main.py wiring
│   │   └── preview.py                   # Final review & deploy
│   │
│   ├── 🌳 arbormind/                    # ArborMind Control Layer (45 files)
│   │   ├── phase_1/                     # State · Fingerprint · Failure Memory
│   │   ├── phase_2/                     # Attention · Taxonomy · Mutation Authority
│   │   ├── phase_3/                     # Governor · Convergence · Mutation Law
│   │   ├── adapters/                    # FAST V2 ↔ ArborMind bridge
│   │   └── persistence/                 # SQLite backend (failure/directive/lineage)
│   │
│   ├── 🧠 core/                         # Domain Primitives (14 files)
│   │   ├── step_outcome.py              # Success/Failure taxonomy enums
│   │   ├── failure_boundary.py          # Isolation enforcement decorator
│   │   ├── guard.py                     # Orchestration safety guard
│   │   ├── config.py                    # Application settings (pydantic-settings)
│   │   ├── types.py                     # Shared type definitions
│   │   └── ...                          # (+9 supporting modules)
│   │
│   ├── 💡 llm/                          # LLM Integration (13 files)
│   │   ├── adapter.py                   # Unified LLM interface
│   │   ├── artifact_enforcement.py      # HDAP output enforcement
│   │   ├── prompts/                     # Per-agent prompts (Marcus/Derek/Victoria/Luna)
│   │   └── providers/                   # Gemini · OpenAI · Anthropic · Ollama
│   │
│   ├── 🔧 tools/                        # Tool System (10 files)
│   │   ├── tools.py                     # 37 tool definitions
│   │   ├── implementations.py           # All implementations (~93KB)
│   │   ├── planner.py                   # Tool planner
│   │   ├── executor.py                  # Tool plan executor
│   │   └── registry.py                  # Tool registry
│   │
│   ├── 🐳 sandbox/                      # Docker Sandbox (7 files)
│   │   ├── sandbox_manager.py           # Main sandbox orchestration
│   │   ├── pool.py                      # Container pool management
│   │   ├── health_monitor.py            # Container health checks
│   │   ├── log_streamer.py              # Real-time log streaming
│   │   └── preview_manager.py           # Preview server management
│   │
│   ├── 🔍 supervision/                  # Quality Gates (4 files)
│   │   ├── supervisor.py                # Marcus supervision layer
│   │   ├── quality_gate.py              # Quality thresholds
│   │   └── tiered_review.py             # Tiered review system
│   │
│   ├── ✅ validation/                   # Code Validation
│   │   ├── static_validator.py          # AST + static analysis
│   │   └── syntax_validator.py          # Syntax checking
│   │
│   ├── 📊 tracking/                     # Telemetry
│   ├── 📦 models/                       # Pydantic/Beanie models
│   ├── 🗄️ db/                           # MongoDB/Beanie setup
│   ├── 🔗 agents/                       # Agent caller wrappers
│   ├── 📚 lib/                          # Shared libraries (WebSocket, secrets)
│   ├── 🛠️ utils/                        # Utilities (entity discovery, parser, etc.)
│   └── 🔄 workflow/                     # Workflow engine entry point
│
├── templates/                           # Project templates (85 files)
├── scripts/                             # ArborMind integration scripts
│   ├── apply_all_boundaries.py          # Apply failure boundary to all handlers
│   ├── apply_failure_boundary.py        # Single handler boundary application
│   └── integrate_manifest.py           # Manifest integration tool
├── ArborMind/                           # Research documents
│   ├── ArborMind Research.txt           # Full whitepaper (1136 lines)
│   └── Equation.docx                    # Mathematical formulation
├── ARBORMIND_IMPLEMENTATION_PLAN.md     # Phase-by-phase implementation guide
├── ARBORMIND_CONFLICTS.md               # FAST V2 authority conflict resolutions
├── PHASE_0_FINAL_AUDIT.md              # Pre-integration audit results
├── CONSOLIDATION_PLAN.md               # Codebase consolidation plan
├── FILE_STRUCTURE.md                    # Full annotated file listing
├── requirements.txt                     # Python dependencies
├── requirements.lock                    # Pinned dependency tree
└── .env.example                         # Environment variable template
```

<br />

---

<br />

## 📖 API Reference

### Generation

```http
POST /api/workspace/{project_id}/generate
Content-Type: application/json

{
  "prompt": "Create a task management app with projects and deadlines"
}
```

### WebSocket — Live Progress

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${projectId}`);

ws.onmessage = (event) => {
  const { type, step, agent, message } = JSON.parse(event.data);
  // Types: STEP_START | AGENT_LOG | STEP_COMPLETE | ERROR | WORKFLOW_COMPLETE
};
```

### Full Endpoint Reference

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/api/workspace/{id}/generate` | Start generation workflow |
| `GET`  | `/api/workspace/{id}` | Workspace details & status |
| `GET`  | `/api/workspace/{id}/files` | List all generated files |
| `DELETE` | `/api/workspace/{id}` | Delete workspace |
| `POST` | `/api/sandbox/{id}/start` | Start Docker preview sandbox |
| `POST` | `/api/sandbox/{id}/stop` | Stop Docker preview sandbox |
| `GET`  | `/api/projects` | List all projects |
| `POST` | `/api/projects` | Create new project |
| `DELETE` | `/api/projects/{id}` | Delete project |
| `GET`  | `/api/providers` | List configured LLM providers |
| `GET`  | `/api/health` | System health check |
| `GET`  | `/api/tracking` | Telemetry & metrics |

<br />

---

<br />

## 🚀 Quick Start

### Prerequisites

> ⚠️ **All three must be running** before the backend will start successfully.

| Requirement | Version | Notes |
|:------------|:--------|:------|
| **Python** | 3.11+ | `python --version` |
| **MongoDB** | 6.0+ | Must be running on port 27017 |
| **Docker** | Latest | Must be running — required for sandbox & tests |

### Installation

```bash
# 1. Navigate to backend
cd Backend

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — add your API keys (see below)

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```

### Environment Variables

```env
# ── Required ──────────────────────────────────────────────────────
GEMINI_API_KEY=your_gemini_key_here
MONGO_URL=mongodb://localhost:27017/gencode

# ── LLM Provider (optional — defaults to Gemini) ──────────────────
LLM_PROVIDER=gemini                  # gemini | openai | anthropic | ollama
LLM_MODEL=gemini-2.0-flash-exp

# ── Optional Providers ────────────────────────────────────────────
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# ── Observability (optional) ──────────────────────────────────────
LOG_LEVEL=INFO
SENTRY_DSN=your_sentry_dsn_here
```

### Access Points

| URL | Description |
|:----|:------------|
| `http://localhost:8000` | API base |
| `http://localhost:8000/docs` | Swagger UI (interactive) |
| `http://localhost:8000/redoc` | ReDoc (readable) |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/metrics` | Prometheus metrics |

<br />

---

<br />

## 🤖 The Agent Team

| Agent | Role | Primary Steps |
|:------|:-----|:-------------|
| **Marcus** | Senior Reviewer & QA Lead | `analysis`, `screenshot_verify`, `contracts`, `preview_final` |
| **Victoria** | System Architect | `architecture` |
| **Derek** | Full-Stack Engineer | `frontend_mock`, `backend_models`, `backend_impl`, `testing_backend`, `frontend_integration` |
| **Luna** | QA & E2E Test Specialist | `testing_frontend` |
| **Reggie** | DevOps & Infrastructure | `system_integration`, sandbox management |

<br />

---

<br />

## 📦 Dependencies

| Category | Packages |
|:---------|:---------|
| **Web Framework** | `fastapi 0.122`, `uvicorn[standard] 0.38`, `pydantic 2.12` |
| **Database** | `motor 3.7`, `beanie 2.0` (async MongoDB ODM) |
| **HTTP** | `httpx 0.28`, `aiohttp 3.12` |
| **Docker** | `docker 7.0` (Python SDK) |
| **Security** | `cryptography 46.0`, `slowapi 0.1` (rate limiting) |
| **Observability** | `sentry-sdk 2.43`, `prometheus-fastapi-instrumentator 7.0` |
| **AI / Math** | `numpy 2.2` |
| **File Handling** | `aiofiles 25.1`, `python-multipart 0.0.20`, `pyyaml 6.0` |
| **Testing** | `pytest 8.4`, `pytest-asyncio 0.25`, `pytest-cov 6.0`, `pytest-mock 3.14` |

<br />

---

<br />

<div align="center">

### Part of [GenCode Studio](../README.md)

**⚙️ Powered by FastAPI · MongoDB · Google Gemini · 🌳 ArborMind**

<br />

<sub>The brain behind intelligent, self-healing code generation</sub>

</div>