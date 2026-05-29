# app/workflow/engine.py
"""
V4 Workflow Engine — Scaffold + Entry Point Stub

V3 Sentinel cognitive loop has been permanently removed.

This file retains:
- run_workflow()          — project scaffolding (templates → disk)
- resume_workflow()       — entry point called by WebSocket handler
- autonomous_agent_workflow() — backwards-compat alias

V4 execution kernel will be wired here in Stage 1.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.orchestration.state import WorkflowStateManager, CURRENT_MANAGERS
from app.core.logging import log


async def run_workflow(
    project_id: str,
    description: str,
    workspaces_path: Path,
    manager: Any,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Start a new workflow for a project.

    Phase 1 (this version): Scaffolds the project directory from templates.
    Phase 2 (Stage 1): Wires V4 Execution Kernel here.
    """
    log("WORKFLOW", f"▶️ run_workflow called for {project_id}")

    # Guard: atomically check and mark as running
    can_start = await WorkflowStateManager.try_start_workflow(project_id)
    if not can_start:
        log("WORKFLOW", f"⚠️ Workflow already running for {project_id}, ignoring duplicate request")
        return

    log("WORKFLOW", f"✅ Workflow guard passed, starting for {project_id}")

    final_project_path = workspaces_path / project_id
    temp_dir_name = f".tmp_scaffold_{project_id}"
    project_path = workspaces_path / temp_dir_name

    if project_path.exists():
        shutil.rmtree(project_path)
    project_path.mkdir(parents=True, exist_ok=True)

    try:
        base_templates = settings.paths.base_dir / "backend" / "templates"

        # ── Backend Seed ──
        backend_dest = project_path / "backend"
        backend_dest.mkdir(parents=True, exist_ok=True)

        backend_seed = base_templates / "backend" / "seed"
        if backend_seed.exists():
            def agent_artifact_filter(src, names):
                ignored = []
                for name in names:
                    if name == "models.py" and "app" in str(src):
                        ignored.append(name)
                    if "routers" in str(src) and name.endswith(".py") and name != "__init__.py":
                        ignored.append(name)
                return ignored

            shutil.copytree(backend_seed, backend_dest, dirs_exist_ok=True, ignore=agent_artifact_filter)
        else:
            log("WORKFLOW", "⚠️ Missing Backend Seed Template!")

        # Ensure routers __init__.py exists
        (backend_dest / "app" / "routers").mkdir(exist_ok=True, parents=True)
        if not (backend_dest / "app" / "routers" / "__init__.py").exists():
            (backend_dest / "app" / "routers" / "__init__.py").write_text("# Routers package\n", encoding="utf-8")

        # ── Test Templates ──
        tests_dest = backend_dest / "tests"
        tests_dest.mkdir(parents=True, exist_ok=True)
        if not (tests_dest / "__init__.py").exists():
            (tests_dest / "__init__.py").write_text("# Tests package\n", encoding="utf-8")

        test_template_src = backend_seed / "tests" / "test_contract_api.template"
        if test_template_src.exists():
            shutil.copy2(test_template_src, tests_dest / "test_contract_api.template")

        # ── Frontend Seed ──
        frontend_dest = project_path / "frontend"
        frontend_dest.mkdir(parents=True, exist_ok=True)

        frontend_seed = base_templates / "frontend" / "seed"
        if frontend_seed.exists():
            shutil.copytree(frontend_seed, frontend_dest, dirs_exist_ok=True)

        frontend_base = base_templates / "frontend"
        for item in frontend_base.iterdir():
            if item.name in ["seed", "reference"]:
                continue
            if item.is_file():
                shutil.copy2(item, frontend_dest / item.name)
            elif item.is_dir() and item.name == "src":
                src_dir = frontend_dest / "src"
                for src_item in item.rglob("*"):
                    if src_item.is_file():
                        rel_path = src_item.relative_to(item)
                        if "components/ui" in str(rel_path).replace("\\", "/"):
                            continue
                        dest_path = src_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        if not dest_path.exists():
                            shutil.copy2(src_item, dest_path)
            elif item.is_dir() and item.name == "public":
                shutil.copytree(item, frontend_dest / "public", dirs_exist_ok=True)

        # ── Frontend Tests ──
        (frontend_dest / "tests").mkdir(parents=True, exist_ok=True)

        # ── Docker Infrastructure ──
        backend_tmpl = base_templates / "backend"
        for docker_file in ["Dockerfile", ".dockerignore"]:
            if (backend_tmpl / docker_file).exists():
                shutil.copy2(backend_tmpl / docker_file, backend_dest / docker_file)

        frontend_tmpl = base_templates / "frontend"
        for docker_file in ["Dockerfile", ".dockerignore"]:
            if (frontend_tmpl / docker_file).exists():
                shutil.copy2(frontend_tmpl / docker_file, frontend_dest / docker_file)

        docker_tmpl = base_templates / "docker"
        if docker_tmpl.exists() and (docker_tmpl / "docker-compose.yml").exists():
            shutil.copy2(docker_tmpl / "docker-compose.yml", project_path / "docker-compose.yml")

        (frontend_dest / ".env").write_text(
            "# Frontend Environment Variables\nVITE_API_URL=http://localhost:8001/api\n",
            encoding="utf-8",
        )

        # Atomic commit
        if final_project_path.exists():
            shutil.rmtree(final_project_path)
        shutil.move(str(project_path), str(final_project_path))
        project_path = final_project_path

    except Exception as e:
        log("WORKFLOW", f"Failed to scaffold project: {e}")
        if project_path.exists() and "tmp_scaffold" in str(project_path):
            try:
                shutil.rmtree(project_path)
            except Exception as cleanup_err:
                log("WORKFLOW", f"Cleanup failed (non-fatal): {cleanup_err}")
        await WorkflowStateManager.stop_workflow(project_id)
        return

    # ── V4 Stage 1: Lock execution substrate ──
    from app.sentinel.runtime.execution_kernel import get_kernel
    kernel = get_kernel()
    await kernel.lock_substrate_after_scaffold(
        project_id=project_id,
        project_path=project_path,
    )

    # ── V4 Execution Kernel entry point (Stage 6) ──
    try:
        from app.orchestration.sentinel_runtime import SentinelRuntime
        runtime = SentinelRuntime()
        success = await runtime.explore_and_project(
            project_id=project_id,
            project_path=project_path,
            user_request=description
        )
        if success:
            log("WORKFLOW", f"✅ V4 Initial Scaffold projection complete for {project_id}")
            try:
                import asyncio
                from app.sandbox import get_sandbox
                from app.utils.path_utils import get_project_path
                log("WORKFLOW", f"🐳 Auto-initializing Docker Sandbox for {project_id}...")
                sb_manager = get_sandbox()
                await sb_manager.create_sandbox(project_id, get_project_path(project_id))
                asyncio.create_task(sb_manager.start_sandbox(project_id, wait_healthy=True))
                log("WORKFLOW", f"⚡ Docker Sandbox boot task launched successfully!")
            except Exception as sb_err:
                log("WORKFLOW", f"⚠️ Failed to auto-initialize sandbox: {sb_err}")
        else:
            log("WORKFLOW", f"❌ V4 Initial Scaffold projection failed for {project_id}")
    except Exception as e:
        log("WORKFLOW", f"❌ V4 Scaffold execution error: {e}")
    finally:
        await WorkflowStateManager.stop_workflow(project_id)


async def autonomous_agent_workflow(
    project_id: str,
    description: str,
    workspaces_path: Path,
    manager: Any,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """Backwards-compatible alias."""
    await run_workflow(project_id, description, workspaces_path, manager, provider, model)


async def resume_workflow(
    project_id: str,
    user_message: str,
    manager: Any,
    workspaces_dir: Path,
) -> None:
    """
    Resume a paused workflow OR start a refinement pass.
    V4 Execution Kernel will be wired here in Stage 1.
    """
    paused = await WorkflowStateManager.get_paused_state(project_id)
    project_path = workspaces_dir / project_id

    provider = settings.llm.default_provider
    model = settings.llm.default_model

    if paused:
        log("WORKFLOW", f"Resuming paused workflow for {project_id}")
        await WorkflowStateManager.resume_workflow(project_id)
        provider = paused.get("provider") or provider
        model = paused.get("model") or model
    else:
        if project_path.exists():
            log("WORKFLOW", f"Starting refinement pass for {project_id}")
        else:
            log("WORKFLOW", f"No project found for {project_id}, cannot resume/refine")
            return

    can_start = await WorkflowStateManager.try_start_workflow(project_id)
    if not can_start:
        log("WORKFLOW", f"⚠️ Workflow already running for {project_id}, ignoring")
        return

    # ── V4 Execution Kernel entry point (Stage 6) ──
    try:
        from app.orchestration.sentinel_runtime import SentinelRuntime
        runtime = SentinelRuntime()
        success = await runtime.explore_and_project(
            project_id=project_id,
            project_path=project_path,
            user_request=user_message
        )
        if success:
            log("WORKFLOW", f"✅ V4 Refinement/Exploration complete for {project_id}")
            try:
                import asyncio
                from app.sandbox import get_sandbox
                from app.utils.path_utils import get_project_path
                log("WORKFLOW", f"🐳 Auto-initializing Docker Sandbox for {project_id}...")
                sb_manager = get_sandbox()
                await sb_manager.create_sandbox(project_id, get_project_path(project_id))
                asyncio.create_task(sb_manager.start_sandbox(project_id, wait_healthy=True))
                log("WORKFLOW", f"⚡ Docker Sandbox boot task launched successfully!")
            except Exception as sb_err:
                log("WORKFLOW", f"⚠️ Failed to auto-initialize sandbox: {sb_err}")
        else:
            log("WORKFLOW", f"❌ V4 Refinement/Exploration failed for {project_id}")
    except Exception as e:
        log("WORKFLOW", f"❌ V4 Orchestration execution error: {e}")
    finally:
        await WorkflowStateManager.stop_workflow(project_id)


async def resume_from_checkpoint_workflow(
    project_id: str,
    description: str,
    workspaces_path: Path,
    manager: Any,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> bool:
    """
    Resume a workflow from a saved checkpoint (UI triggered).
    V4 Execution Kernel will be wired here in Stage 1.
    """
    has_progress = await WorkflowStateManager.has_progress(project_id)
    if not has_progress:
        log("WORKFLOW", f"No saved progress for {project_id}, cannot resume")
        return False

    project_path = workspaces_path / project_id
    if not project_path.exists():
        log("WORKFLOW", f"Project directory not found: {project_path}")
        return False

    can_start = await WorkflowStateManager.try_start_workflow(project_id)
    if not can_start:
        log("WORKFLOW", f"⚠️ Workflow already running for {project_id}")
        return False

    # ── V4 Execution Kernel entry point (Stage 6) ──
    try:
        from app.orchestration.sentinel_runtime import SentinelRuntime
        runtime = SentinelRuntime()
        success = await runtime.explore_and_project(
            project_id=project_id,
            project_path=project_path,
            user_request=description
        )
        if success:
            log("WORKFLOW", f"✅ V4 Checkpoint recovery cycle complete for {project_id}")
        else:
            log("WORKFLOW", f"❌ V4 Checkpoint recovery cycle failed for {project_id}")
    except Exception as e:
        log("WORKFLOW", f"❌ V4 Checkpoint recovery error: {e}")
    finally:
        await WorkflowStateManager.stop_workflow(project_id)
    return True
