<div align="center">
  <img src="docs/images/GenxAI Logo 1.png" alt="GenxAI Logo" width="300" />

  <h1>GenxAI Studio V4</h1>
  <p><strong>The Next-Generation Agentic Coding Environment</strong></p>

  <p>
    <a href="#features">Features</a> •
    <a href="#sentinel-architecture">Sentinel</a> •
    <a href="#getting-started">Getting Started</a> •
    <a href="#benchmarks">Benchmarks</a>
  </p>
</div>

---

## 🌟 Overview

**GenxAI Studio V4** is a revolutionary AI-powered development environment designed to build, refactor, and manage codebases autonomously. Powered by the **Sentinel Cognitive Architecture**, it doesn't just generate code—it understands, verifies, repels failures, and iteratively repairs applications until they reach deterministic perfection.

<div align="center">
  <img src="docs/images/GenxAI Studio.png" alt="GenxAI Studio Interface" width="800" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);" />
</div>

---

## ✨ Features

- **Autonomous Workspace Generation**: Generate full-stack applications (Frontend + Backend) from simple conversational intents.
- **AST-Aware Projection**: Manipulate code at the Abstract Syntax Tree level for surgical precision.
- **Cognitive Faculties**: Sub-agents like *Victoria* (UI), *Derek* (API), *Luna* (Database), and *Reggie* (Workflow) collaboratively design the universe of thought.
- **Immutable Execution Kernel**: Transactions are safely committed, verified, and rolled back if they breach integrity.
- **Real-time Telemetry & Visualization**: Track the AI's internal cognition, memory hits, and cluster analyses in real-time.

---

## 🧠 The Sentinel Architecture

<div align="center">
  <img src="docs/images/Sentinel.png" alt="Sentinel Architecture" width="800" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);" />
</div>

Sentinel is the cognitive engine driving GenxAI Studio. Unlike traditional linear agents, Sentinel employs a **10-Phase Recursive Recovery Loop** built on the philosophy that *not every experience deserves memory*.

1. **Projection**: Attempt structural modifications via AST Projector.
2. **Verification**: Multi-layered integrity gates ensure the code compiles and renders.
3. **Failure Analysis**: Failures are dynamically clustered and embedded.
4. **Governance (Marcus)**: The Marcus agent decides if a failure is recoverable (`REPAIR`) or fatal (`REJECT`).
5. **Candidate Memory**: Failures are encoded into `sentinel_validation.db` as untrusted candidates, awaiting validation.
6. **Universe of Thought**: Cognitive faculties propose multiple parallel architectural fixes.
7. **Branch Evaluation**: The Repulsion Engine actively penalizes branches that match historical failures.
8. **Selection**: The optimal, stable topology is selected.
9. **Finalization**: Candidate memory is committed upon successful repair.
10. **Telemetry**: Full flush of the internal cognitive logs for analysis.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **MongoDB**

### 1. Start the Backend

```bash
cd Backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Start the uvicorn server
uvicorn app.main:app --reload
```

### 2. Start the Frontend

```bash
cd Frontend
npm install
npm run dev
```

### 3. Run the Sentinel Benchmark Suite

To test the resilience of the cognitive loop against synthetic failures:
```bash
cd Sentinel_Validation
python sentinel_benchmark_runner.py
```
*(View the results using `python view_telemetry.py`)*

---

<div align="center">
  <p>Built with ⚡ by <strong>GenxAI Labz</strong></p>
</div>
