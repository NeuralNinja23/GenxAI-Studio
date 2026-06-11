import os
import shutil
from pathlib import Path
from typing import Union, Optional, List
from app.core.config import settings

class WorkspaceArchitecture:
    # ── 1. Directory Layout Authority ──
    FRONTEND_DIR = "frontend"
    BACKEND_DIR = "backend"
    STAGING_DIR = ".genx_staging"
    ARCHIVE_DIR = "archive"

    # ── 2. Absolute Path Generation ──
    @classmethod
    def frontend_root(cls, workspace: Path) -> Path:
        """Resolve absolute frontend path on disk."""
        return cls.resolve(workspace, cls.FRONTEND_DIR)

    @classmethod
    def backend_root(cls, workspace: Path) -> Path:
        """Resolve absolute backend path on disk."""
        return cls.resolve(workspace, cls.BACKEND_DIR)

    @classmethod
    def staging_root(cls, workspace: Path) -> Path:
        """Resolve absolute staging path on disk."""
        return cls.resolve(workspace, cls.STAGING_DIR)

    @classmethod
    def archive_root(cls, workspace: Path) -> Path:
        """Resolve absolute archive path on disk."""
        return cls.resolve(workspace, cls.ARCHIVE_DIR)

    @classmethod
    def frontend_file(cls, workspace: Path, relative_subpath: Union[str, Path]) -> Path:
        """Generate canonical absolute path to a frontend file."""
        return cls.frontend_root(workspace) / Path(relative_subpath)

    @classmethod
    def backend_file(cls, workspace: Path, relative_subpath: Union[str, Path]) -> Path:
        """Generate canonical absolute path to a backend file."""
        return cls.backend_root(workspace) / Path(relative_subpath)

    # ── 3. Canonical Relative Path Emission ──
    @classmethod
    def to_workspace_relative(cls, workspace: Path, path: Union[str, Path]) -> str:
        """
        Convert any absolute path or staged path into a canonical workspace-root-relative path:
        - Forward slashes (/)
        - Workspace-root relative (no absolute or staged prefixes)
        - Lowercase root directories (e.g. C:\\workspace\\.genx_staging\\Frontend\\src\\App.tsx -> frontend/src/App.tsx)
        """
        p = Path(path)
        workspace_abs = workspace.resolve()
        
        if p.is_absolute():
            p_abs = p.resolve()
        else:
            p_abs = (workspace_abs / p).resolve()

        try:
            rel = p_abs.relative_to(workspace_abs)
        except ValueError:
            # Fallback for paths outside workspace_abs or casing anomalies
            p_str = str(p_abs).replace("\\", "/").strip("/")
            for prefix in [".genx_staging", ".genx_backup", ".project.rollback_backup"]:
                if prefix in p_str:
                    p_str = p_str.split(prefix, 1)[-1].strip("/")
            workspace_name = workspace.name
            if workspace_name in p_str:
                p_str = p_str.split(workspace_name, 1)[-1].strip("/")
            rel = Path(p_str)
            
        parts = list(rel.parts)
        
        # Clean staging and backup subpath roots
        while parts and parts[0] in [".genx_staging", ".genx_backup", ".project.rollback_backup"]:
            parts.pop(0)
            
        # Standardize root folders to lowercase
        if parts:
            if parts[0].lower() == cls.FRONTEND_DIR:
                parts[0] = cls.FRONTEND_DIR
            elif parts[0].lower() == cls.BACKEND_DIR:
                parts[0] = cls.BACKEND_DIR
                
        return "/".join(parts)

    # ── 4. Workspace Validation & Repair (Governance) ──
    @classmethod
    def validate_workspace(cls, workspace: Path) -> List[str]:
        """
        Scans workspace directory for casing and structural deviations:
        - Checks REQUIRED:
          - frontend (exists strictly lowercase)
          - backend (exists strictly lowercase)
        - Checks FORBIDDEN (incorrect casing variations of required roots):
          - Frontend, Backend, FrontEnd, BackEnd
        - Checks duplicate casing roots
        - Checks multiple staging roots
        Returns violations.
        """
        violations = []
        if not workspace.exists():
            return [f"Workspace path does not exist: {workspace}"]

        found_entries = list(workspace.iterdir())
        found_dirs = [e.name for e in found_entries if e.is_dir()]
        
        # 1. Check Required roots exist strictly in lowercase
        if cls.FRONTEND_DIR not in found_dirs:
            violations.append(f"Missing required frontend directory: '{cls.FRONTEND_DIR}'")
        if cls.BACKEND_DIR not in found_dirs:
            violations.append(f"Missing required backend directory: '{cls.BACKEND_DIR}'")

        # 2. Check Forbidden casing variations
        forbidden_casing = {"Frontend", "Backend", "FrontEnd", "BackEnd"}
        for d in found_dirs:
            if d in forbidden_casing:
                violations.append(f"Forbidden directory casing detected: '{d}'")

        # 3. Check Duplicate casing roots (e.g. 'frontend' and 'Frontend' both present)
        lowercased_dirs = [d.lower() for d in found_dirs]
        if len(lowercased_dirs) != len(set(lowercased_dirs)):
            seen = set()
            duplicates = set()
            for d in lowercased_dirs:
                if d in seen:
                    duplicates.add(d)
                seen.add(d)
            violations.append(f"Duplicate casing roots detected in workspace: {list(duplicates)}")

        # 4. Check Multiple staging roots
        staging_roots = [d for d in found_dirs if "staging" in d.lower() or d.startswith(".genx_staging")]
        if len(staging_roots) > 1:
            violations.append(f"Multiple staging directories detected: {staging_roots}")

        return violations

    @classmethod
    def validate_workspace_topology(cls, workspace: Path) -> List[str]:
        """
        Validates the workspace structural topology.
        Checks:
          - frontend/package.json exists
          - backend/app exists
          - .genx_staging is not nested
          - archive is outside staging
          - no duplicate frontend/backend roots
        Returns violations.
        """
        violations = []
        if not workspace.exists():
            return [f"Workspace path does not exist: {workspace}"]

        # 1. frontend/package.json exists
        frontend_pkg = workspace / cls.FRONTEND_DIR / "package.json"
        try:
            resolved_pkg = cls.resolve(workspace, f"{cls.FRONTEND_DIR}/package.json")
            if not resolved_pkg.exists():
                violations.append(f"package.json missing from frontend: '{cls.FRONTEND_DIR}/package.json' not found.")
        except Exception:
            if not frontend_pkg.exists():
                violations.append("package.json missing from frontend.")

        # 2. backend/app exists
        backend_app = workspace / cls.BACKEND_DIR / "app"
        try:
            resolved_app = cls.resolve(workspace, f"{cls.BACKEND_DIR}/app")
            if not resolved_app.exists() or not resolved_app.is_dir():
                violations.append(f"app directory missing from backend: '{cls.BACKEND_DIR}/app' not found.")
        except Exception:
            if not backend_app.exists() or not backend_app.is_dir():
                violations.append("app directory missing from backend.")

        # 3. .genx_staging is not nested (must only be at root level)
        for p in workspace.rglob(".genx_staging"):
            if p.is_dir() and p.parent.resolve() != workspace.resolve():
                violations.append(f"Nested staging directory detected: '{p.relative_to(workspace)}'")

        # 4. archive is outside staging
        staging_root = workspace / cls.STAGING_DIR
        for p in workspace.rglob(cls.ARCHIVE_DIR):
            if p.is_dir() and staging_root.resolve() in p.resolve().parents:
                violations.append(f"Archive directory found inside staging: '{p.relative_to(workspace)}'")

        # 5. no duplicate frontend/backend roots
        found_dirs = [e.name for e in workspace.iterdir() if e.is_dir()]
        lowercased_dirs = [d.lower() for d in found_dirs]
        if lowercased_dirs.count(cls.FRONTEND_DIR) > 1:
            violations.append("Duplicate frontend roots detected in workspace.")
        if lowercased_dirs.count(cls.BACKEND_DIR) > 1:
            violations.append("Duplicate backend roots detected in workspace.")

        return violations

    @classmethod
    def validate_and_repair_workspace(cls, workspace: Path) -> List[str]:
        """
        Validates workspace. If violations exist and strict_workspace_governance is False,
        attempts to automatically repair casing deviations (Frontend -> frontend, Backend -> backend).
        Returns remaining violations.
        """
        violations = cls.validate_workspace(workspace) + cls.validate_workspace_topology(workspace)
        if not violations:
            return []

        if settings.strict_workspace_governance:
            return violations

        # Tolerant Repair Mode
        if workspace.exists():
            for entry in workspace.iterdir():
                if entry.is_dir():
                    name = entry.name
                    if name.lower() == cls.FRONTEND_DIR and name != cls.FRONTEND_DIR:
                        temp_target = workspace / f"{cls.FRONTEND_DIR}_temp"
                        target = workspace / cls.FRONTEND_DIR
                        try:
                            if temp_target.exists():
                                if temp_target.is_dir():
                                    shutil.rmtree(temp_target)
                                else:
                                    temp_target.unlink()
                            os.rename(entry, temp_target)
                            os.rename(temp_target, target)
                        except Exception as e:
                            violations.append(f"Failed to repair frontend casing: {e}")
                    elif name.lower() == cls.BACKEND_DIR and name != cls.BACKEND_DIR:
                        temp_target = workspace / f"{cls.BACKEND_DIR}_temp"
                        target = workspace / cls.BACKEND_DIR
                        try:
                            if temp_target.exists():
                                if temp_target.is_dir():
                                    shutil.rmtree(temp_target)
                                else:
                                    temp_target.unlink()
                            os.rename(entry, temp_target)
                            os.rename(temp_target, target)
                        except Exception as e:
                            violations.append(f"Failed to repair backend casing: {e}")

        # Re-evaluate
        return cls.validate_workspace(workspace) + cls.validate_workspace_topology(workspace)

    # ── 5. Normalization (Reserved for External Outputs) ──
    @classmethod
    def normalize_external_path(cls, path: Union[str, Path]) -> str:
        """Standardizes external outputs, compiler logs, and legacy references to POSIX relative paths."""
        p_str = str(path).replace("\\", "/").strip("/")
        parts = p_str.split("/")
        if parts:
            if parts[0].lower() == cls.FRONTEND_DIR:
                parts[0] = cls.FRONTEND_DIR
            elif parts[0].lower() == cls.BACKEND_DIR:
                parts[0] = cls.BACKEND_DIR
        return "/".join(parts)

    # ── 6. Physical Directory Lookup / Resolution ──
    @classmethod
    def resolve(cls, base: Path, target: Union[str, Path]) -> Path:
        """
        Lookup target path relative to base.
        Under strict_workspace_governance: throws FileNotFoundError if target directory has incorrect casing.
        Otherwise: resolves case-insensitively for backwards compatibility.
        """
        target_path = Path(target)
        if settings.strict_workspace_governance:
            # Normalize target path to remove . and ..
            normalized_target = Path(os.path.normpath(target_path))
            if normalized_target.is_absolute():
                try:
                    normalized_target = normalized_target.relative_to(base.resolve())
                except ValueError:
                    pass
            
            if normalized_target.is_absolute():
                current = Path(normalized_target.anchor)
                parts = normalized_target.parts[1:]
            else:
                current = base.resolve()
                parts = normalized_target.parts

            for part in parts:
                if part in ('.', '..'):
                    current = (current / part).resolve()
                    continue
                part_lower = part.lower()
                exists_case_insensitive = False
                casing_match = False
                if current.exists() and current.is_dir():
                    for entry in current.iterdir():
                        if entry.name.lower() == part_lower:
                            exists_case_insensitive = True
                            if entry.name == part:
                                casing_match = True
                                current = entry
                            break
                if exists_case_insensitive:
                    if not casing_match:
                        raise FileNotFoundError(f"Strict workspace governance: casing mismatch for '{part}' in '{current}'")
                else:
                    current = current / part
            return base / target_path

        current = base
        for part in target_path.parts:
            part_lower = part.lower()
            found = None
            if current.exists() and current.is_dir():
                for entry in current.iterdir():
                    if entry.name.lower() == part_lower:
                        found = entry
                        break
            if found is not None:
                current = found
            else:
                current = current / part
        return current
