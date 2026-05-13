# app/core/files.py
"""
Centralized file operations and persistence.

CONSOLIDATED from:
- app/core/file_writer.py
- app/orchestration/file_persistence.py (atomic write logic)
"""
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.logging import log
from app.core.llm_output_integrity import validate_llm_files, LLMOutputIntegrityError


def atomic_write(path: Path, content: str) -> bool:
    """
    Atomically write text to a file using tmp file + rename.
    Prevents partial writes.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
        return True
    except Exception as e:
        log("FILE", f"❌ Write failed: {path} - {e}")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return False


def convert_files_list_to_dict(files: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Convert list of {"path": ..., "content": ...} to dict {path: content}.
    """
    return {f["path"]: f["content"] for f in files if "path" in f and "content" in f}


async def write_validated_files(
    project_path: Path,
    files: List[Dict[str, str]],
    step: str,
) -> int:
    """
    Validate and write LLM-generated files to disk.
    Uses atomic writes for safety.
    """
    if not files:
        return 0
    
    # Convert to dict format for validation
    files_dict = convert_files_list_to_dict(files)
    
    # Validate (raises on error)
    validate_llm_files(files_dict, step)
    
    # Write files
    written = 0
    for path, content in files_dict.items():
        try:
            full_path = project_path / path
            if atomic_write(full_path, content):
                written += 1
            else:
                log(step, f"❌ Failed to write {path}")
        except Exception as e:
            log(step, f"❌ Check failed for {path}: {e}")
    
    return written


# ═══════════════════════════════════════════════════════════════════════════
# LEGACY WRAPPERS (Keep for backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════

async def persist_agent_output(
    manager: Any,
    project_id: str,
    project_path: Path,
    parsed: Dict[str, Any],
    step: str,
) -> int:
    """Legacy wrapper for write_validated_files."""
    files = parsed.get("files", [])
    return await write_validated_files(project_path, files, step)


def validate_file_output(
    parsed: Dict[str, Any],
    step: str,
    max_files: int = 10,
) -> Dict[str, Any]:
    """Legacy wrapper - validates and returns the same parsed dict."""
    files = parsed.get("files", [])
    if not files:
        return parsed
    
    files_dict = convert_files_list_to_dict(files)
    validate_llm_files(files_dict, step)
    return parsed


async def safe_write_llm_files(
    manager: Any,
    project_id: str,
    project_path: Path,
    files: List[Dict[str, str]],
    step_name: str,
) -> int:
    """Legacy compatibility wrapper for write_validated_files."""
    return await write_validated_files(project_path, files, step_name)
