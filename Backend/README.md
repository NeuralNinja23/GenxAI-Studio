<div align="center">


<br />
<br />

# ⚙️ GenCode Studio Backend

### **The AI Engine That Powers Code Generation**

<br />

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Beanie-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Docker](https://img.shields.io/badge/Docker-Sandbox-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

<br />

The **Backend** is where the magic happens — a sophisticated orchestration system that coordinates AI agents, manages workflows, and produces production-ready code.

<br />

> *Receives a prompt → Orchestrates 12 intelligent steps → Delivers tested, deployable code*

<br />

[⚡ Pipeline](#-the-fast-v2-pipeline) • [🛡️ Reliability](#-evidence-based-reliability) • [🚀 Quick Start](#-quick-start)

<br />

---

</div>

<br />

## ✨ Core Capabilities

<div align="center">

### ⚡ FAST V2 Orchestrator
The intelligent workflow engine: **12 atomic steps** with dependency barriers · **Budget tracking** per step · **Checkpointing** for resume · **Cross-step context** sharing

### 🧠 Intelligent Orchestration
Smart workflow execution: **V≠K attention** architecture · **Semantic decision** making · **Adaptive strategies**

### 🛡️ Evidence-Based Reliability
Automatic reliability enforcement: **Environment** vs **Cognitive** failure separation · **Selective retries** for infra (evidence steps) · **Quarantine** for logic failures · **One-Shot Policy** for causal steps (no infinite loops)

### 🐳 Docker Sandbox
Isolated testing environment: **Containerized** pytest runs · **Playwright E2E** testing · **MongoDB** test instances · **Full isolation** per project

</div>

<br />

---

<br />

## ⚡ The FAST V2 Pipeline

<div align="center">

<img src="docs/images/fast_pipeline.png" alt="FAST V2 Pipeline" width="900" />

<br />
<sub><i>4-Phase Linear Pipeline — One-Shot execution with strict separation of Causal and Evidence steps</i></sub>

</div>

<br />

The FAST V2 Orchestrator executes a carefully designed sequence of steps:

### 🔍 Phase 1 — Analysis
> **Marcus** → `analysis` · Extract entities, classify archetype  
> **Victoria** → `architecture` · Design system, create schemas

### 🎨 Phase 2 — Frontend  
> **Derek** → `frontend_mock` · Generate React UI with mock data  
> **Marcus** → `screenshot_verify` · Visual QA review  
> **Marcus** → `contracts` · Define OpenAPI specifications

### ⚙️ Phase 3 — Backend
> **Derek** → `backend_models` · Generate Beanie/MongoDB models  
> **Derek** → `backend_impl` · Create FastAPI routers  
> **Script** → `system_integration` · Wire main.py & requirements

### 🧪 Phase 4 — Testing & Deploy
> **Derek** → `testing_backend` · Run pytest in Docker  
> **Derek** → `frontend_integration` · Connect UI to real APIs  
> **Luna** → `testing_frontend` · Playwright E2E tests  
> **Marcus** → `preview_final` · Final review & deployment

<br />

---

<br />

## 🧠 Intelligent Orchestration

<div align="center">

<br />
<sub><i>Smart workflow execution with attention-based routing</i></sub>

</div>

<br />

The **FAST V2 Orchestrator** powers intelligent decision-making throughout the pipeline:

<table>
<tr>
<td width="33%" align="center">

### 🧠 Attention Router
**V≠K Architecture**

```python
# Query: User request
# Key: Option descriptions  
# Value: Behavior configs

result = await route_decision(
    "Fix React bug",
    tool_options
)
# → Smart tool selection
```

</td>
<td width="33%" align="center">

### 📊 Execution Policies
**Step-Aware Modes**

```python
# Causal steps: One-shot
# Evidence steps: Retry OK
POLICY = {
    "generation": "artifact",
    "testing": "freeform",
    "analysis": "structured",
}
```

</td>
<td width="33%" align="center">

### 🔮 Pattern Explorer
**Creative Solutions**

```python
# Foreign pattern injection
explorer.inject_patterns(
    context,
    creativity=0.3
)
# → Novel approaches
```

</td>
</tr>
</table>

<br />

---

<br />

## 🛡️ Evidence-Based Reliability
 
 <div align="center">
 
 <img src="docs/images/failure_classification.png" alt="Failure Classification" width="600" />
 
 <br />
 <sub><i>Strict failure taxonomy with explicit containment strategies</i></sub>
 
 </div>
 
 <br />
 
 The system enforces a strict **One-Shot Policy** for all causal steps, relying on precise failure classification rather than infinite retry loops:
 
 <table>
 <tr>
 <td width="50%">
 
 ### 🏷️ Outcome Taxonomy
 
 | Type | Logic | Handling |
 |:-----|:------|:---------|
 | **SUCCESS** | Steps verify OK | Proceed |
 | **ENVIRONMENT_FAILURE** | Infra/Network/Docker | **Retry** (Evidence steps only) |
 | **COGNITIVE_FAILURE** | Agents/Tests/Reasoning | **Isolate** (No auto-healing) |
 | **HARD_FAILURE** | Logical Impossibility | **Stop** Workflow |
 
 </td>
 <td width="50%">
 
 ### 🛡️ Isolation Strategy
 
 ```
 Step Failure
      ↓
 Failure Classifier
      ↓
 ┌────┴────┐
 │  INFRA  │  COGNITIVE  │
 │ (Retry) │  (Isolate)  │
 └────┬────┘      │
      │        Quarantine
      ↓           ↓
  Continue    Human Review
 ```
 
 </td>
 </tr>
 </table>
 
 <br />
 
 **Core Files:**
 
 | File | Purpose |
 |:-----|:--------|
 | `step_outcome.py` | Taxonomy definitions (Success, Env, Cog, Hard) |
 | `failure_classifier.py` | Semantic analysis of errors |
 | `failure_boundary.py` | Runtime enforcement layer |
 | `retry_policy.py` | Selective retries for infrastructure only |
 
 <br />
 
 ---

<br />

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│   │   REST API  │   │  WebSocket  │   │   Health    │               │
│   │  /api/*     │   │  /ws/{id}   │   │   /health   │               │
│   └──────┬──────┘   └──────┬──────┘   └─────────────┘               │
│          │                 │                                          │
│          ▼                 ▼                                          │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                   FAST V2 ORCHESTRATOR                       │   │
│   │   • 12 Steps  • Dependencies  • Budget  • Checkpoints       │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                        │
│          ┌───────────────────┼───────────────────┐                   │
│          ▼                   ▼                   ▼                   │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│   │  Orchestrator│     │   Agents    │     │ Supervision │           │
│   │  Intelligence│     │ Marcus/Derek│     │   Quality   │           │
│   └─────────────┘     └─────────────┘     └─────────────┘           │
│          │                   │                   │                   │
│          └───────────────────┴───────────────────┘                   │
│                              │                                        │
│                              ▼                                        │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                      LLM PROVIDERS                           │   │
│   │        Gemini (default)  │  OpenAI  │  Anthropic            │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                        │
│          ┌───────────────────┴───────────────────┐                   │
│          ▼                                       ▼                   │
│   ┌─────────────┐                         ┌─────────────┐           │
│   │ Validation  │                         │ Persistence │           │
│   │ AST + Safety│                         │ File Writer │           │
│   └─────────────┘                         └─────────────┘           │
│          │                                       │                   │
│          └───────────────────┬───────────────────┘                   │
│                              ▼                                        │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                  DOCKER SANDBOX                              │   │
│   │      Backend Tests  │  Frontend Tests  │  Preview           │   │
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
│   ├── main.py                  # FastAPI entry point
│   │
│   ├── 📡 api/                  # REST Endpoints (9 files)
│   │   ├── workspace.py         # Generation API
│   │   ├── projects.py          # Project CRUD
│   │   └── sandbox.py           # Docker management
│   │
│   ├── ⚡ orchestration/        # FAST V2 Core (31 files)
│   │   ├── fast_orchestrator.py # Main orchestrator
│   │   ├── healing_pipeline.py  # Self-healing
│   │   ├── budget_manager.py    # Cost tracking
│   │   └── checkpoint.py        # Progress saving
│   │
│   ├── 📋 handlers/             # Step Handlers (20 files)
│   │   ├── analysis.py          # Entity extraction
│   │   ├── architecture.py      # System design
│   │   ├── backend.py           # Router generation
│   │   └── testing_*.py         # Test execution
│   │
│   ├── 🧠 orchestration/        # FAST V2 Intelligence
│   │   ├── router.py            # Attention routing
│   │   ├── evolution.py         # Self-evolution
│   │   └── explorer.py          # Pattern discovery
│   │
│   ├── 🤖 agents/               # Agent wrappers
│   ├── 🧠 llm/                  # LLM integration (13 files)
│   ├── 🛡️ supervision/          # Quality gates (4 files)
│   ├── ✅ validation/           # Pre-write checks
│   ├── 💾 persistence/          # File writing
│   ├── 🐳 sandbox/              # Docker (7 files)
│   ├── 📊 tracking/             # Telemetry
│   ├── 📚 learning/             # Pattern store
│   └── 🔧 tools/                # Agent tools
│
├── templates/                    # Project templates (85 files)
├── tests/                        # Unit tests
└── requirements.txt              # Dependencies
```

<br />

---

<br />

## 🌐 API Reference

### Generation

```http
POST /api/workspace/{project_id}/generate
Content-Type: application/json

{
  "prompt": "Create a task management app with projects and deadlines"
}
```

### WebSocket Events

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${projectId}`);

ws.onmessage = (event) => {
  const { type, step, agent, message } = JSON.parse(event.data);
  // Types: STEP_START, AGENT_LOG, STEP_COMPLETE, ERROR, WORKFLOW_COMPLETE
};
```

### Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/api/workspace/{id}/generate` | Start generation |
| `GET` | `/api/workspace/{id}` | Workspace details |
| `GET` | `/api/workspace/{id}/files` | List files |
| `POST` | `/api/sandbox/{id}/start` | Start preview |
| `GET` | `/api/projects` | List projects |

<br />

---

<br />

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|:------------|:--------|
| **Python** | 3.11+ |
| **Docker** | Latest |
| **MongoDB** | 6.0+ |

### Installation

```bash
# Navigate to backend
cd Backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your GEMINI_API_KEY

# Run
uvicorn app.main:app --reload --port 8000
```

### Environment

```env
# Required
GEMINI_API_KEY=your_key_here
MONGO_URL=mongodb://localhost:27017/gencode

# Optional
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash-exp
LOG_LEVEL=INFO
```

### Access

| URL | Description |
|:----|:------------|
| `http://localhost:8000` | API |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |

<br />

---

<br />

<div align="center">

### Part of [GenCode Studio](../README.md)

**⚡ Powered by FastAPI • MongoDB • Google Gemini**

<br />

<sub>The brain behind intelligent code generation</sub>

</div>