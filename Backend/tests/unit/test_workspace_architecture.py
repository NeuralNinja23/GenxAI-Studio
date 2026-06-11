import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.studio.architecture.workspace_architecture import WorkspaceArchitecture

def test_to_workspace_relative():
    workspace = Path("C:/Users/JARVIS/Desktop/GenxAI Studio/workspaces/kanban-board")
    
    # 1. Standard lowercase path
    p1 = "frontend/src/App.tsx"
    assert WorkspaceArchitecture.to_workspace_relative(workspace, p1) == "frontend/src/App.tsx"

    # 2. Capital Frontend path
    p2 = "Frontend/src/App.tsx"
    assert WorkspaceArchitecture.to_workspace_relative(workspace, p2) == "frontend/src/App.tsx"

    # 3. Absolute staged path
    p3 = "C:/Users/JARVIS/Desktop/GenxAI Studio/workspaces/kanban-board/.genx_staging/Backend/app/main.py"
    assert WorkspaceArchitecture.to_workspace_relative(workspace, p3) == "backend/app/main.py"

    # 4. Path with backslashes
    p4 = "Frontend\\src\\components\\Button.tsx"
    assert WorkspaceArchitecture.to_workspace_relative(workspace, p4) == "frontend/src/components/Button.tsx"


def test_validate_workspace():
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        
        # Scenario 1: Empty workspace (should fail because frontend and backend are missing)
        violations = WorkspaceArchitecture.validate_workspace(workspace)
        assert any("Missing required frontend directory" in v for v in violations)
        assert any("Missing required backend directory" in v for v in violations)

        # Scenario 2: Correctly structured workspace
        (workspace / "frontend").mkdir()
        (workspace / "backend").mkdir()
        violations = WorkspaceArchitecture.validate_workspace(workspace)
        assert not violations

        # Scenario 3: Incorrect casing root (forbidden casing)
        (workspace / "frontend").rmdir()
        (workspace / "Frontend").mkdir()
        violations = WorkspaceArchitecture.validate_workspace(workspace)
        assert any("Forbidden directory casing detected" in v for v in violations)


def test_validate_workspace_topology():
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "frontend").mkdir()
        (workspace / "backend").mkdir()

        # package.json and app directory missing
        violations = WorkspaceArchitecture.validate_workspace_topology(workspace)
        assert any("package.json missing from frontend" in v for v in violations)
        assert any("app directory missing from backend" in v for v in violations)

        # Fix structural elements
        with open(workspace / "frontend" / "package.json", "w") as f:
            f.write("{}")
        (workspace / "backend" / "app").mkdir()

        violations = WorkspaceArchitecture.validate_workspace_topology(workspace)
        assert not violations

        # Nested staging directory
        (workspace / "frontend" / "src" / ".genx_staging").mkdir(parents=True)
        violations = WorkspaceArchitecture.validate_workspace_topology(workspace)
        assert any("Nested staging directory detected" in v for v in violations)


def test_validate_and_repair_workspace():
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        
        # Create incorrect casing directories
        (workspace / "Frontend").mkdir()
        (workspace / "Backend").mkdir()
        with open(workspace / "Frontend" / "package.json", "w") as f:
            f.write("{}")
        (workspace / "Backend" / "app").mkdir()

        # Run with strict_workspace_governance = False (controlled by mock or config settings)
        with patch.object(settings, 'strict_workspace_governance', False):
            violations = WorkspaceArchitecture.validate_and_repair_workspace(workspace)
            # Should have automatically repaired the directories
            assert not violations
            names = os.listdir(workspace)
            assert "frontend" in names
            assert "backend" in names
            assert "Frontend" not in names
            assert "Backend" not in names


def test_resolve_casing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "frontend" / "src").mkdir(parents=True)
        with open(workspace / "frontend" / "src" / "App.tsx", "w") as f:
            f.write("// App")

        # Tolerant resolve (governance = False)
        with patch.object(settings, 'strict_workspace_governance', False):
            resolved = WorkspaceArchitecture.resolve(workspace, "Frontend/src/App.tsx")
            assert resolved.name == "App.tsx"
            assert resolved.parent.name == "src"
            assert resolved.parent.parent.name == "frontend"

        # Strict resolve raises FileNotFoundError if requested with wrong casing
        with patch.object(settings, 'strict_workspace_governance', True):
            with pytest.raises(FileNotFoundError):
                WorkspaceArchitecture.resolve(workspace, "Frontend/src/App.tsx")
