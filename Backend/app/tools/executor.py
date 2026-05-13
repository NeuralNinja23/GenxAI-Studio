# app/tools/executor.py
"""
Tool Plan Executor

LINEAR EXECUTION ONLY:
- No loops
- No retries
- No self-healing
- No reflection

Just execution of an explicit plan.

OBSERVATION:
Every tool invocation is recorded:
- Before: record_tool_invocation_start
- After: record_tool_invocation_end
"""

from datetime import datetime, timezone
from typing import Any, Optional
import traceback

from app.tools.planning import (
    ToolPlan,
    ToolInvocationPlan,
    ToolInvocationResult,
    ToolPlanExecutionResult,
    StepFailure,
)
from app.core.logging import log




# ═══════════════════════════════════════════════════════════════════════════════
# P0.1: HDAP PARSING + FILE WRITING (CRITICAL FIX)
# ═══════════════════════════════════════════════════════════════════════════════

async def _parse_and_write_hdap_files(
    output: Any,
    branch: Any,
    step: str,
) -> list[str]:
    """
    Extract files from subagentcaller output and write to disk.
    
    CRITICAL: This function is the SOLE OWNER of artifact materialization.
    
    Handles THREE output structures:
    1. Pre-parsed files: output.output.files = [{"path": "...", "content": "..."}]
    2. Raw HDAP text: output.raw_generation = "<<<FILE path=...>>>..."
    3. Nested dict: output.output.raw_generation
    
    Returns:
        List of file paths that were written
    """
    from pathlib import Path
    import re
    
    try:
        # Get project path from branch
        project_path = None
        if hasattr(branch, "project_path"):
            project_path = Path(branch.project_path)
        elif isinstance(branch, dict):
            project_path = Path(branch.get("project_path", "."))
        
        if not project_path:
            log("TOOL-EXEC", f"   ⚠️ Cannot write files: no project_path in branch")
            return []
        
        files_to_write = []
        
        # ═══════════════════════════════════════════════════════════════
        # STRATEGY 1: Check for pre-parsed files (from marcus_call_sub_agent)
        # Structure: output.output.files = [{"path": "...", "content": "..."}]
        # ═══════════════════════════════════════════════════════════════
        if isinstance(output, dict):
            inner_output = output.get("output", {})
            if isinstance(inner_output, dict):
                parsed_files = inner_output.get("files", [])
                if parsed_files and isinstance(parsed_files, list):
                    for f in parsed_files:
                        if isinstance(f, dict) and f.get("path") and f.get("content"):
                            files_to_write.append({
                                "path": f["path"],
                                "content": f["content"]
                            })
                    if files_to_write:
                        log("TOOL-EXEC", f"   📦 Found {len(files_to_write)} pre-parsed files")
        
        # ═══════════════════════════════════════════════════════════════
        # STRATEGY 2: Parse raw HDAP text if no pre-parsed files
        # ═══════════════════════════════════════════════════════════════
        if not files_to_write:
            raw_text = None
            
            # Try multiple extraction paths
            if isinstance(output, dict):
                # Path A: output.raw_generation
                raw_text = output.get("raw_generation")
                
                # Path B: output.output (if string)
                if not raw_text:
                    inner = output.get("output")
                    if isinstance(inner, str):
                        raw_text = inner
                    elif isinstance(inner, dict):
                        # Path C: output.output.raw_generation
                        raw_text = inner.get("raw_generation")
            elif isinstance(output, str):
                raw_text = output
            
            if raw_text and isinstance(raw_text, str):
                # Parse HDAP markers
                # Pattern: <<<FILE path="...">>>> content <<<END_FILE>>>
                # Also try: <<<FILE path="...">>> content <<<END_FILE>>>
                patterns = [
                    r'<<<FILE\s+path=["\']([^"\']+)["\']>>>>(.*?)<<<END_FILE>>>',
                    r'<<<FILE\s+path=["\']([^"\']+)["\']>>>(.*?)<<<END_FILE>>>',
                ]
                
                matches = []
                for pattern in patterns:
                    matches = re.findall(pattern, raw_text, re.DOTALL)
                    if matches:
                        break
                
                for file_path, content in matches:
                    files_to_write.append({
                        "path": file_path.strip(),
                        "content": content.strip()
                    })
                
                if files_to_write:
                    log("TOOL-EXEC", f"   📝 Parsed {len(files_to_write)} files from HDAP")
        
        # ═══════════════════════════════════════════════════════════════
        # WRITE FILES TO DISK
        # ═══════════════════════════════════════════════════════════════
        if not files_to_write:
            log("TOOL-EXEC", f"   ⚠️ No files found in output for step '{step}'")
            return []
        
        written_files = []
        
        for file_info in files_to_write:
            file_path = file_info["path"]
            content = file_info["content"]
            
            # Resolve full path
            full_path = project_path / file_path
            
            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(content, encoding="utf-8")
            written_files.append(str(full_path))
            
            log("TOOL-EXEC", f"      ✏️ Wrote: {file_path}")
        
        log("TOOL-EXEC", f"   ✅ Materialized {len(written_files)} artifact(s)")
        return written_files
        
    except Exception as e:
        log("TOOL-EXEC", f"   ⚠️ HDAP file extraction failed: {e}")
        import traceback
        log("TOOL-EXEC", f"      {traceback.format_exc()[:200]}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVATION HOOKS
# ═══════════════════════════════════════════════════════════════════════════════

def record_tool_invocation_start(
    plan_id: str,
    invocation: ToolInvocationPlan,
    step: str,
    agent: str,
) -> None:
    """
    Record the start of a tool invocation.
    
    This is where observation happens.
    """
    log("TOOL-EXEC", f"▶️ [{invocation.tool_name}] Starting ({invocation.reason})")


def record_tool_invocation_end(
    plan_id: str,
    result: ToolInvocationResult,
    step: str,
    agent: str,
) -> None:
    """
    Record the end of a tool invocation.
    
    PHASE 3.5: Records tool trace + CLASSIFIED failure event (if applicable)
    
    CRITICAL INVARIANT:
        A failure that does not halt execution is STILL a failure.
        Only gating decides continuation — not existence.
    """
    status = "✅" if result.success else "❌"
    files_count = len(result.output.get("_written_files", [])) if isinstance(result.output, dict) else 0
    file_info = f", files={files_count}" if files_count > 0 else ""
    log("TOOL-EXEC", f"{status} [{result.tool_name}] {result.duration_ms}ms{file_info}")


# ═══════════════════════════════════════════════════════════════════════════════
# LINEAR EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

async def execute_tool_plan(
    plan: ToolPlan,
    branch: Any,
    stop_on_failure: bool = True,
) -> ToolPlanExecutionResult:
    """
    Execute a tool plan LINEARLY.
    
    Rules:
    - No loops
    - No retries
    - No self-healing
    - No reflection
    
    Just execution of an explicit plan.
    
    Args:
        plan: The immutable ToolPlan to execute
        branch: The execution branch context
        stop_on_failure: If True, stop on first required tool failure
    
    Returns:
        ToolPlanExecutionResult with all invocation results
    """
    from app.tools.registry import run_tool
    
    # Removed verbose start logs - planner already logs tool chain
    
    results: list[ToolInvocationResult] = []
    final_output = None
    overall_success = True
    overall_error = None
    total_start = datetime.now(timezone.utc)
    
    for i, invocation in enumerate(plan.sequence):
        # Start log handled by record_tool_invocation_start()
        
        # Record start
        record_tool_invocation_start(
            plan_id=plan.plan_id,
            invocation=invocation,
            step=plan.step,
            agent=plan.agent,
        )
        
        # Execute
        started_at = datetime.now(timezone.utc)
        try:
            # ═══════════════════════════════════════════════════════════════
            # POST Tool Wiring: Inject previous tool output for validation tools
            # ═══════════════════════════════════════════════════════════════
            tool_args = dict(invocation.args)  # Copy to avoid mutation
            
            if invocation.tool_name in ("syntaxvalidator", "static_code_validator"):
                # Get code from written files (if any)
                if final_output and isinstance(final_output, dict):
                    written_files = final_output.get("_written_files", [])
                    if written_files:
                        # Read the first written file for validation
                        try:
                            from pathlib import Path
                            first_file = Path(written_files[0])
                            if first_file.exists():
                                code = first_file.read_text(encoding="utf-8")
                                tool_args["code"] = code
                                # Detect language from extension
                                ext = first_file.suffix.lower()
                                if ext == ".py":
                                    tool_args["language"] = "python"
                                elif ext in (".js", ".jsx", ".ts", ".tsx"):
                                    tool_args["language"] = "javascript"
                        except Exception:
                            pass  # Non-fatal
                
                # If still no code, skip this tool
                if not tool_args.get("code"):
                    log("TOOL-EXEC", f"⏭️ [{invocation.tool_name}] Skipped (no code to validate)")
                    result = ToolInvocationResult(
                        invocation_id=invocation.invocation_id,
                        tool_name=invocation.tool_name,
                        success=True,
                        output={"skipped": True, "reason": "No code to validate"},
                        error=None,
                        duration_ms=0,
                        started_at=started_at.isoformat(),
                        ended_at=started_at.isoformat(),
                    )
                    results.append(result)
                    continue  # Skip to next tool
            
            output = await run_tool(invocation.tool_name, tool_args)
            ended_at = datetime.now(timezone.utc)
            
            # Determine success from output
            success = True
            error = None
            
            if isinstance(output, dict):
                # Check for explicit failure indicators
                # Note: subagentcaller uses "passed", most others use "success"
                if output.get("success") is False:
                    success = False
                    error = output.get("error") or output.get("message") or "Tool returned failure"
                elif output.get("passed") is False:
                    # subagentcaller returns passed=False for HDAP/truncation failures
                    success = False
                    issues = output.get("issues", [])
                    if issues and isinstance(issues[0], dict):
                        error = issues[0].get("description", "Agent returned passed=False")
                    else:
                        error = "Agent returned passed=False"
                elif output.get("error"):
                    success = False
                    error = output.get("error")
            
            result = ToolInvocationResult(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                success=success,
                output=output,
                error=error,
                duration_ms=int((ended_at - started_at).total_seconds() * 1000),
                started_at=started_at.isoformat(),
                ended_at=ended_at.isoformat(),
            )
            
            # ═══════════════════════════════════════════════════════════════
            # P0.1 FIX: HDAP Parsing + File Writing for subagentcaller
            # ═══════════════════════════════════════════════════════════════
            # When subagentcaller succeeds, parse HDAP markers and write files
            if success and invocation.tool_name == "subagentcaller":
                files_written = await _parse_and_write_hdap_files(
                    output=output,
                    branch=branch,
                    step=plan.step,
                )
                if files_written:
                    # Attach written files to output for downstream
                    if isinstance(output, dict):
                        output["_written_files"] = files_written
                        result = ToolInvocationResult(
                            invocation_id=invocation.invocation_id,
                            tool_name=invocation.tool_name,
                            success=True,
                            output=output,
                            error=None,
                            duration_ms=result.duration_ms,
                            started_at=result.started_at,
                            ended_at=result.ended_at,
                        )
            
            # Track last successful output
            if success:
                final_output = output
            
        except Exception as e:
            ended_at = datetime.now(timezone.utc)
            tb = traceback.format_exc()
            
            result = ToolInvocationResult(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                success=False,
                output=None,
                error=f"{str(e)}\n{tb}",
                duration_ms=int((ended_at - started_at).total_seconds() * 1000),
                started_at=started_at.isoformat(),
                ended_at=ended_at.isoformat(),
            )
        
        # Record end
        record_tool_invocation_end(
            plan_id=plan.plan_id,
            result=result,
            step=plan.step,
            agent=plan.agent,
        )
        
        results.append(result)
        
        # End log handled by record_tool_invocation_end()
        
        # Handle failure
        if not result.success:
            if invocation.required and stop_on_failure:
                overall_success = False
                overall_error = f"Required tool '{invocation.tool_name}' failed: {result.error}"
                
                raise StepFailure(
                    step=plan.step,
                    tool_name=invocation.tool_name,
                    error=result.error or "Unknown error",
                    invocation_id=invocation.invocation_id,
                )
            # Optional failures already logged above - no extra noise
    
    total_end = datetime.now(timezone.utc)
    total_duration = int((total_end - total_start).total_seconds() * 1000)
    # Plan completion logged implicitly by step completion
    
    return ToolPlanExecutionResult(
        plan_id=plan.plan_id,
        step=plan.step,
        success=overall_success,
        results=results,
        final_output=final_output,
        error=overall_error,
        total_duration_ms=total_duration,
    )
