import os
from typing import Optional
from app.studio.architecture.workspace_architecture import WorkspaceArchitecture

class ImportResolver:
    """
    Domain-Aware Import Resolver for AST Generator.
    Handles distinct import strategies for Backend (Python) and Frontend (React/TSX).
    """
    FRONTEND_MODE = "alias"  # can be "alias" or "relative"

    @classmethod
    def resolve(cls, source_path: str, target_path: str, domain: Optional[str] = None) -> str:
        if not target_path:
            raise ValueError("ImportResolver received empty target path")
            
        if not source_path:
            raise ValueError("ImportResolver received empty source path")

        # Determine domain if not explicitly provided
        if not domain:
            if target_path.endswith((".tsx", ".ts", ".jsx", ".js")):
                domain = "react"
            elif target_path.endswith(".py"):
                domain = "python"
            else:
                domain = "python" # fallback

        if domain == "python":
            # e.g., Backend/app/models/customer.py -> app.models.customer
            module = target_path.replace(".py", "")
            module = module.replace("\\", "/").replace("/", ".")
            if module.lower().startswith("backend."):
                module = module[8:]
            return module

        elif domain == "react":
            if cls.FRONTEND_MODE == "alias":
                module = target_path.rsplit(".", 1)[0]
                lower_module = module.lower()
                prefix_lower = f"{WorkspaceArchitecture.FRONTEND_DIR.lower()}/src/"
                if prefix_lower in lower_module:
                    idx = lower_module.index(prefix_lower) + len(prefix_lower)
                    return f"@/{module[idx:]}"
                # If target is not in Frontend/src/, fallback to relative pathing
            
            # relative mode (or fallback from alias if target not in src)
            source_dir = os.path.dirname(source_path)
            if not source_dir:
                source_dir = "."
                
            relative_path = os.path.relpath(target_path, start=source_dir)
            relative_path = relative_path.replace("\\", "/")
            
            if not relative_path.startswith("."):
                relative_path = f"./{relative_path}"
                
            # strip extension
            relative_path = relative_path.rsplit(".", 1)[0]
            return relative_path

        return target_path
