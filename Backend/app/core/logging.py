import sys
import os
from datetime import datetime
from typing import Any, Optional, List

_active_project_id = None

def set_active_project_id(project_id: Optional[str]) -> None:
    global _active_project_id
    _active_project_id = project_id

class LoggerStreamWrapper:
    def __init__(self, original_stream):
        self.original_stream = original_stream
        self._is_wrapped_logger = True

    def write(self, buf):
        self.original_stream.write(buf)
        global _active_project_id
        if _active_project_id:
            try:
                from pathlib import Path
                root_dir = Path(__file__).parent.parent.parent.parent
                logs_dir = root_dir / "Logs"
                logs_dir.mkdir(parents=True, exist_ok=True)
                log_file = logs_dir / f"{_active_project_id}.txt"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(buf)
            except Exception:
                pass

    def flush(self):
        self.original_stream.flush()

if not hasattr(sys.stdout, "_is_wrapped_logger"):
    sys.stdout = LoggerStreamWrapper(sys.stdout)
if not hasattr(sys.stderr, "_is_wrapped_logger"):
    sys.stderr = LoggerStreamWrapper(sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE E4: LOG FILTERING
# ═══════════════════════════════════════════════════════════════════════════════
# Only these 5 log classes are shown at INFO level
# Everything else is gated behind DEBUG

INFO_SCOPES = {
    "SENTINEL",    # Brain logs
    "FAST",         # Muscle logs
    "FAST-V2",      # Step lifecycle
    "PLANNER",      # Execution intent  
    "TOOL-EXEC",    # Actual execution
    "SUPERVISION",  # Review verdict
    "TOKENS",       # Token usage
    "HDAP",         # File protocol
    "LOCKFILE",     # Cache hits
    "WORKFLOW",     # Scaffold and entry points
    "SENTINEL_RUNTIME",# Cognitive controllers
    "KERNEL",       # Execution kernel and transactions
    "PROJECTOR",    # AST file projections
    "COGNITION",    # Bounded branch search
    "PATCH_DEBUG",  # Debug patches
    "BRANCH_SELECTION", # Branch selection diagnostics
    "GRAPH_VERIFY",
    "TELEMETRY",
}

# DEBUG-only scopes (hidden by default)
DEBUG_SCOPES = {
    "PREFLIGHT",
    "COMPONENT_COPIER",
    "FILTER",
    "DISCOVERY",
    "OPTIMIZATION",
    "ATTENTION",
    "BOUNDARY",
    "RUNTIME",
}

# Check if DEBUG mode is enabled
DEBUG_MODE = os.getenv("GENCODE_DEBUG", "false").lower() == "true"


def safe_print(text: str) -> None:
    """Print helper that safely handles Windows terminal CP1252 encoding constraints."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='replace').decode(encoding))


def log(scope: str, message: str, data: Any = None, project_id: Optional[str] = None) -> None:
    """
    Unified logging function for GenxAI Studio.
    
    PHASE E4: Only INFO_SCOPES are shown by default.
    Set GENCODE_DEBUG=true to see all scopes.
    """
    # Filter non-essential logs unless DEBUG mode
    if not DEBUG_MODE and scope not in INFO_SCOPES:
        return  # Silently skip
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] [{scope}]"
    
    if project_id:
        short_id = project_id[:8]
        prefix += f" [{short_id}]"
        
    safe_print(f"{prefix} {message}")
    
    if data:
        safe_print(f"  Data: {data}")
    
    sys.stdout.flush()


def log_section(scope: str, title: str, project_id: Optional[str] = None) -> None:
    """
    Log a section header with visual separator.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    safe_print(f"\n{'='*60}")
    if project_id:
        safe_print(f"[{timestamp}] [{scope}] [{project_id[:8]}] {title}")
    else:
        safe_print(f"[{timestamp}] [{scope}] {title}")
    safe_print(f"{'='*60}")
    sys.stdout.flush()


def log_thinking(scope: str, thinking: str, project_id: Optional[str] = None, max_lines: int = 10) -> None:
    """
    Log agent thinking/reasoning with proper formatting.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] [{scope}]"
    if project_id:
        prefix += f" [{project_id[:8]}]"
    
    safe_print(f"\n{prefix} 💭 THINKING:")
    lines = str(thinking).split('\n')
    for line in lines[:max_lines]:
        safe_print(f"  {line}")
    if len(lines) > max_lines:
        safe_print(f"  ... ({len(lines) - max_lines} more lines)")
    sys.stdout.flush()


def log_files(scope: str, files: List[dict], project_id: Optional[str] = None) -> None:
    """
    Log file list summary.
    """
    # Silent as requested
    pass


def log_result(scope: str, approved: bool, quality: int, issues: List[str] = None, project_id: Optional[str] = None) -> None:
    """
    Log review result with quality score.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] [{scope}]"
    if project_id:
        prefix += f" [{project_id[:8]}]"
    
    if approved:
        safe_print(f"\n{prefix} ✅ APPROVED - Quality: {quality}/10")
    else:
        safe_print(f"\n{prefix} ⚠️ REJECTED - Quality: {quality}/10")
        if issues:
            safe_print(f"{prefix} Issues found:")
            for i, issue in enumerate(issues[:5]):
                safe_print(f"  {i+1}. {issue}")
    
    safe_print(f"{'='*60}\n")
    sys.stdout.flush()
