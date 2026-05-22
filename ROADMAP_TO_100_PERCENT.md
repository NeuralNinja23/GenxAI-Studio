# Road to 100%: GenxAI Studio V3 Final Implementation Plan

This document outlines the exact, exhaustive 7-step plan to take GenxAI Studio V3 from its current state (~70%) to a 100% feature-complete, research-grade product matching the exact specifications of the ArborMind whitepaper and LinkedIn positioning.

---

## Step 1: Implement Reggie (Deployment Engineer Agent)
**Goal:** Add the 5th agent responsible for taking validated code and deploying it.

* [ ] **Update Constants:** Open `app/core/constants.py` and add `REGGIE = "Reggie"` to the `AgentName` class.
* [ ] **Create Persona:** Create `app/llm/prompts/reggie.py`. Define `REGGIE_PROMPT` instructing him to act as a DevOps engineer who outputs JSON configurations for Docker, networking, and environment variables.
* [ ] **Add to Sub-Agents:** Update `app/agents/sub_agents.py` `marcus_call_sub_agent()` to recognize the "Reggie" routing key and use his specific prompt.
* [ ] **Create Handler:** Create `app/handlers/deployment.py`. This handler will execute after Luna finishes testing.
* [ ] **Update Workflow Steps:** Add `DEPLOYMENT` as a step in `WorkflowStep` in `constants.py` (e.g., Step 10).
* [ ] **FastAPI Router:** Ensure the frontend can trigger the deployment phase specifically via a new API endpoint or WebSocket command.

## Step 2: Build One-Click Deployment Infrastructure
**Goal:** Make Reggie's output actually spin up a live, accessible preview URL.

* [ ] **Define Host Target:** Decide if deployment means spinning up a local container on a public port, or using a tunneling service like Ngrok/Cloudflare Tunnels to make it public.
* [ ] **Build Deployment Manager:** Create `app/sandbox/deployment_manager.py`.
* [ ] **Port Allocation Logic:** Write a function to find an open port on the host machine dynamically.
* [ ] **Docker Compose Override:** Have Reggie generate or modify a `docker-compose.prod.yml` that strips out dev dependencies and maps the public port.
* [ ] **Subprocess Execution:** Write the logic to execute `docker-compose -f docker-compose.prod.yml up -d` autonomously.
* [ ] **WebSocket Broadcast:** Update `WSMessageType.PREVIEW_URL_READY` to send the actual generated URL (e.g., `http://localhost:8080` or the Ngrok URL) back to the UI.
* [ ] **Frontend Update:** Update the React frontend to display a celebratory "Deployment Successful" modal with a clickable link.

## Step 3: ArborMind Persistence (SQLite & FAISS)
**Goal:** Ensure ArborMind permanently remembers failures across different generated projects and server restarts.

* [ ] **Dependencies:** Add `faiss-cpu`, `sqlalchemy`, and an embedding library (or use Gemini's embedding API) to `requirements.txt`.
* [ ] **Database Setup:** Create `app/arbormind/db_setup.py` to initialize a SQLite database (e.g., `failures.db`).
* [ ] **Table Schema:** Create a SQLAlchemy model for `failures` containing: `fingerprint_hash`, `project_id`, `error_type`, `stack_trace`, and `timestamp`.
* [ ] **Vector Index:** Initialize a FAISS index object to store the semantic embeddings of the failed code states.
* [ ] **Embedding Function:** Write a function `get_embedding(code_state)` that converts a failed code file into a 1536-dimensional vector.
* [ ] **Refactor `failure_memory.py`:** Update `record()` to INSERT into SQLite and `.add()` to FAISS instead of just appending to a Python dictionary.
* [ ] **Update State Gate:** Update `is_forbidden()` to perform a FAISS nearest-neighbor search (`index.search()`). If a state is 95% similar to a known failure, block it.

## Step 4: Implement V≠K Attention Routing Mathematics
**Goal:** Upgrade ArborMind's routing from basic scalar addition to the "Transformer-inspired" matrix math.

* [ ] **Dependencies:** Ensure `numpy` is installed.
* [ ] **Refactor `attention.py`:** Delete the current `apply()` function that just adds/subtracts floats.
* [ ] **Define Vectors:** Define fixed-length vectors for `Q` (Current Intent), `K` (Available Strategies/Tools), and `V` (Configurations).
* [ ] **Implement Attraction:** Write the NumPy logic for standard attention: `attraction = softmax(np.dot(Q, K.T) / np.sqrt(d_k))`.
* [ ] **Implement Repulsion:** Write the RBF Kernel function `Kernel(dist) = exp(-dist^2 / 2*sigma^2)`.
* [ ] **Calculate Distances:** For every known failure in the FAISS index, calculate its distance to the current state.
* [ ] **Combine (α):** Write the final equation: `alpha = attraction - (lambda * sum_of_repulsions)`. This returns the mathematical probability of which agent/tool to use next.

## Step 5: Implement EMA-Based Online Learning
**Goal:** Make ArborMind get smarter over time by adjusting routing weights after successes/failures.

* [ ] **Create Learning Module:** Create `app/arbormind/phase_3/learning.py`.
* [ ] **Define EMA Logic:** Write a function `update_weights(current_weights, loss_signal)`.
* [ ] **Math Implementation:** Implement `V_new = (alpha_ema * V_current) + ((1 - alpha_ema) * reward_signal)`.
* [ ] **Hook into Orchestrator:** Open `app/arbormind/adapters/orchestrator.py`. In the success path (around line 371), call the EMA update with a positive reward (e.g., `1.0`).
* [ ] **Hook into Failure:** In the failure path (around line 383), call the EMA update with a negative reward (e.g., `-1.0`).
* [ ] **Persist Weights:** Save the updated `V_new` vector space to SQLite or a JSON file so the "brain" doesn't reset when you restart the FastAPI server.

## Step 6: Parallel Phase Execution (Dynamic DAG)
**Goal:** Reduce generation time by running independent tasks simultaneously.

* [ ] **Map Dependencies:** Create a Dependency Graph dictionary in `constants.py`. For example, `BACKEND_MODELS` requires `ARCHITECTURE`, but `FRONTEND_MOCK` only requires `ARCHITECTURE`. They do not require each other.
* [ ] **Refactor Orchestrator:** Open `app/orchestration/engine.py` (or `fast_orchestrator.py`). Remove the strictly linear `for step in steps:` loop.
* [ ] **Implement Asyncio.gather:** Write an asynchronous DAG runner. Use `asyncio.gather(run_frontend_mock(), run_backend_models())` to fire both agents simultaneously.
* [ ] **Thread-Safe Logging:** Ensure the WebSocket logger (`log()` function) includes the `agent_name` and `thread_id` so UI logs don't get jumbled when two agents are writing at the same time.
* [ ] **Update Frontend UI:** Modify the React UI progress bar. Instead of a single linear track, visualize it as a branching tree or independent checklist where multiple items can be "In Progress" at once.

## Step 7: Architectural Mutation & Self-Healing Integration
**Goal:** Implement the logic where ArborMind autonomously swaps frameworks or architectures if stuck in a loop.

* [ ] **Track Stagnation:** In `orchestrator.py`, ensure the `loss_history` array is correctly tracking failures per step.
* [ ] **Implement `detect_stagnation()`:** Write logic: `if len(loss_history) >= 3 and variance(loss_history[-3:]) < 0.01: return True`.
* [ ] **Define Mutations:** In `mutation_authority.py`, hardcode 3-5 specific architectural pivots (e.g., "Switch ORM to raw SQL", "Change relationship from One-to-Many to Many-to-Many", "Make endpoint asynchronous").
* [ ] **Trigger Pivot:** When stagnation is detected, randomly (or via attention) select a mutation strategy.
* [ ] **Force Rewrites:** Pass the mutation strategy back to Victoria (Architect). Append it to her prompt as an absolute constraint. 
* [ ] **Invalidate Cache:** Clear any cached code files related to the mutated architecture and force Derek to regenerate them based on Victoria's new blueprint.
