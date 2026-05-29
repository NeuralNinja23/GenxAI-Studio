<div align="center">

<img src="docs/images/GenxAI Studio.png" alt="GenxAI Studio" width="100%" />

<br />

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)

<br />

**GenxAI Studio** is an AI-powered code generation platform that transforms natural language descriptions into complete, tested, production-ready full-stack applications.

<br />

> *"Build me a bug tracking system with projects, issues, and user assignments"*
> 
> → **Complete FastAPI backend + React frontend in minutes, not days.**

<br />

[✨ Features](#-key-features) • [🤖 AI Agents](#-meet-the-ai-team) • [🌳 Sentinel](#-sentinel--neural-orchestration) • [🚀 Quick Start](#-quick-start) • [📖 Docs](#-api-reference)

<br />

---

</div>

<br />

## ✨ Key Features

### 🤖 Multi-Agent Intelligence
A specialized team of AI agents work together: **Code Review & Quality Gates** · **Architecture Design & Planning** · **Full-Stack Implementation** · **Automated E2E Testing**

### 🌳 Self-Evolving AI  
Sentinel orchestration engine: **Learns from every generation** · **Adapts strategies in real-time** · **Attention-based smart routing** · **Evidence-based reliability**

### 🛡️ Production-Grade Output
Enterprise-quality code generation: **AST validation before write** · **Pre-flight syntax checks** · **Docker sandbox testing** · **Automatic rollback on failure**

### 🎨 Intelligent UI Design
Smart frontend generation: **6 UI vibes** (Dark, Minimal, Glass...) · **Archetype detection** (SaaS, E-commerce...) · **Modern shadcn/ui components** · **Mobile-first responsive design**

<br />

---

<br />

## 🤖 Meet the AI Team



<table>
<tr>
<td align="center" width="20%">

### 🔵 Marcus
**Senior Architect**

*The Supervisor*

Code review, quality gates, final approval. Ensures every line meets production standards.

</td>
<td align="center" width="20%">

### 🟣 Victoria
**System Architect**

*The Strategist*

Designs system architecture, API contracts, and database schemas from requirements.

</td>
<td align="center" width="20%">

### 🟢 Derek
**Full-Stack Developer**

*The Builder*

Implements React frontends, FastAPI backends, and integrates everything seamlessly.

</td>
<td align="center" width="20%">

### 🟡 Luna
**QA Engineer**

*The Guardian*

Writes and runs Playwright E2E tests, catches bugs before deployment.

</td>
<td align="center" width="20%">

### 🟠 Reggie
**Deployment Agent**

*The Shipper*

Handles environment setup, builds, and one-click deployment pipelines (Planned).

</td>
</tr>
</table>

<br />

---

<br />

## ⚡ The FAST V2 Pipeline



| Phase | Steps | What Happens |
|:------|:------|:-------------|
| **🔍 Analysis** | 1-2 | Understand requirements, extract entities, design architecture |
| **🎨 Frontend** | 3 | Generate React UI with mock data for immediate visual feedback |
| **⚙️ Backend** | 4-7 | Create models, API contracts, FastAPI routers, database integration |
| **🔗 Integration** | 8-9 | Connect frontend to real APIs, visual QA verification |
| **🧪 Testing** | 10-11 | Run pytest backend tests, Playwright E2E tests in Docker |
| **🚀 Deploy** | 12 | Final review, generate preview URL, ready for production |

<br />

---

<br />

## 🌳 Sentinel — Neural Orchestration

<br />

## 🌳 Sentinel — The Orchestration Engine

**Sentinel** is the foundational orchestration infrastructure that powers GenxAI Studio. While GenxAI Studio provides the specialized agents (Marcus, Victoria, Derek, Luna, Reggie) and the software generation context, Sentinel is the engine that dynamically coordinates them.

It manages execution order, resolves dependencies, and schedules the agents across the entire pipeline.

### 🧠 Transformer-Inspired Heuristic Router
Sentinel implements a transformer-inspired heuristic routing system that separates intent matching from strategy scoring, enabling weighted heuristic-based strategy selection rather than simply retrieving the nearest match.

### ⛔ Causal / Evidence Execution (State Gate)
Execution splits into two classes: causal steps (irreversible) and evidence branches (verifiable). Failed states are fingerprinted and permanently blocked from re-execution — preventing the system from getting stuck in retry cascades during long-horizon workflows.

### ⚡ Parallel Pipeline Execution (Planned)
Future versions are designed to execute independent workflow phases concurrently where dependencies allow, reducing end-to-end generation time without compromising correctness.

### 🧬 EMA-Based Adaptive Routing (Planned)
Designed to support Exponential Moving Average (EMA) adaptive routing, Sentinel will eventually learn from workflow outcomes to optimize strategy selection across projects without human feedback.

<br />

---

<br />

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Why |
|:------------|:--------|:----|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 18+ | Frontend build |
| **Docker** | Latest | Sandbox testing |
| **MongoDB** | 6.0+ | Database |

### Installation

```bash
# Clone the repository
git clone https://github.com/NeuralNinja23/GenCode-Studio.git
cd GenCode-Studio

# Backend setup
cd Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Start backend
uvicorn app.main:app --reload --port 8000

# Frontend setup (new terminal)
cd Frontend
npm install
npm run dev
```

### Environment Variables

```env
# 🔑 Required
GEMINI_API_KEY=your_gemini_api_key_here
MONGO_URL=mongodb://localhost:27017/gencode_studio

# ⚙️ Optional
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash-exp
WORKSPACE_ROOT=./workspaces
LOG_LEVEL=INFO

# 🐳 Docker
DOCKER_HOST=npipe:////./pipe/docker_engine    # Windows
# DOCKER_HOST=unix:///var/run/docker.sock     # Linux/Mac
```

<br />

---

<br />

## 🏗️ Architecture

```
GenCode-Studio/
├── 📁 Backend/
│   ├── 📁 app/
│   │   ├── 📁 agents/            # Marcus, Derek, Victoria, Luna
│   │   ├── 📁 sentinel/         # 🌳 Neural orchestration core
│   │   │   ├── router.py         # Attention-based routing
│   │   │   ├── evolution.py      # Self-evolving V-vectors
│   │   │   └── explorer.py       # Pattern exploration
│   │   ├── 📁 orchestration/     # FAST V2 engine
│   │   ├── 📁 persistence/       # File validation & writing
│   │   ├── 📁 sandbox/           # Docker container management
│   │   ├── 📁 tools/             # 30+ injectable tools
│   │   └── main.py               # FastAPI entry point
│   └── 📁 templates/             # shadcn/ui, boilerplate
│
├── 📁 Frontend/
│   └── 📁 src/                   # React application
│
└── 📁 workspaces/                # Generated projects
```

<br />

---

<br />

## 📖 API Reference

### Generate Application

```http
POST /api/workspace/{project_id}/generate
Content-Type: application/json

{
  "prompt": "Create a task management app with projects, tasks, and team collaboration"
}
```

### WebSocket Events

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${workflowId}`);

ws.onmessage = (event) => {
  const { type, step, agent, message } = JSON.parse(event.data);
  
  // Types: STEP_START, AGENT_LOG, STEP_COMPLETE, WORKFLOW_COMPLETE, ERROR
};
```

### Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/api/workspace/{id}` | Get workspace details |
| `GET` | `/api/workspace/{id}/files` | List generated files |
| `POST` | `/api/workspace/{id}/preview` | Start preview server |
| `DELETE` | `/api/workspace/{id}` | Delete workspace |

<br />

---

<br />

## 🛡️ Reliability & Quality

<table>
<tr>
<td width="50%">

### Pre-flight Validation
- ✅ AST syntax parsing for all Python files
- ✅ Empty content detection
- ✅ Bracket balance checking
- ✅ Truncation detection
- ✅ Undefined name checking

</td>
<td width="50%">

### Evidence-Based Reliability
- 🛡️ Strict Environment vs Cognitive separation
- ⛔ One-Shot Policy for causal logic (no loops)
- ↩️ Selective retries for infrastructure only
- 🏥 Automatic environment recovery
- 🔒 Cognitive failure quarantine

</td>
</tr>
</table>

<br />

---

<br />

## 🎨 UI Archetypes & Vibes

GenxAI Studio intelligently detects your app type and applies matching aesthetics:

**Archetypes:** `admin_dashboard` • `ecommerce_store` • `saas_app` • `realtime_collab` • `portfolio_site` • `developer_tools`

**Vibes:** `dark_hacker` • `minimal_light` • `vibrant_modern` • `playful_colorful` • `corporate_clean` • `glassmorphism`

<br />

---

<br />

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details.

```bash
# Fork, clone, then:
git checkout -b feature/amazing-feature
git commit -m 'feat: add amazing feature'
git push origin feature/amazing-feature
# Open a Pull Request
```

<br />

---

<br />

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

<br />

---

<div align="center">

<br />

### Built with ❤️ by [NeuralNinja23](https://github.com/NeuralNinja23)

<br />

**⭐ Star this repo if GenxAI Studio helps you build faster!**

<br />

<sub>GenxAI Studio — From idea to production in minutes, not months.</sub>

<br />
<br />

</div>
