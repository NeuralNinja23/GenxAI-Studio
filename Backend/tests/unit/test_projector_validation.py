import pytest
import json
from pathlib import Path
from app.sentinel.topology.ast_projector import ASTProjector, ProjectorError

def test_validate_empty_response():
    projector = ASTProjector()
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_not_empty("")
    assert exc_info.value.reason == "EMPTY_RESPONSE"

    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_not_empty("   \n   ")
    assert exc_info.value.reason == "EMPTY_RESPONSE"

def test_validate_invalid_json():
    projector = ASTProjector()
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_json(" { malformed json ")
    assert exc_info.value.reason == "INVALID_JSON"

def test_validate_schema():
    projector = ASTProjector()
    # Not a dictionary
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_schema(["not", "a", "dict"])
    assert exc_info.value.reason == "INVALID_PROJECT_SCHEMA"

    # Non-string keys or values
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_schema({"src/main.tsx": 12345})
    assert exc_info.value.reason == "INVALID_PROJECT_SCHEMA"

def test_validate_required_keys():
    projector = ASTProjector()
    
    # Missing everything
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_required_keys({})
    assert exc_info.value.reason == "MISSING_REQUIRED_ARTIFACT"

    # Has manifest but missing entry, config, and source
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_required_keys({"package.json": "{}"})
    assert exc_info.value.reason == "MISSING_REQUIRED_ARTIFACT"

    # Has manifest and entry, but missing config and source
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_required_keys({
            "package.json": "{}",
            "main.tsx": "console.log('hello');"
        })
    assert exc_info.value.reason == "MISSING_REQUIRED_ARTIFACT"

    # Has manifest, entry, and config, but missing source tree
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_required_keys({
            "package.json": "{}",
            "main.tsx": "console.log('hello');",
            "vite.config.ts": "export default {}"
        })
    assert exc_info.value.reason == "MISSING_REQUIRED_ARTIFACT"

    # All criteria met
    valid_data = {
        "package.json": "{}",
        "frontend/src/main.tsx": "console.log('hello');",
        "frontend/vite.config.ts": "export default {}"
    }
    # Should not raise any error
    projector.validate_required_keys(valid_data)

def test_validate_project_shape():
    projector = ASTProjector()

    # Traversal attack
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_project_shape({"../etc/passwd": "content"})
    assert exc_info.value.reason == "INVALID_PROJECT_SHAPE"

    # Rooted path
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_project_shape({"/usr/bin/python": "content"})
    assert exc_info.value.reason == "INVALID_PROJECT_SHAPE"

    # Path too deep (depth > 10)
    deep_path = "a/b/c/d/e/f/g/h/i/j/k/l/m/n.tsx"
    with pytest.raises(ProjectorError) as exc_info:
        projector.validate_project_shape({deep_path: "content"})
    assert exc_info.value.reason == "INVALID_PROJECT_SHAPE"


@pytest.mark.asyncio
async def test_execution_kernel_catches_projector_error(tmp_path):
    from app.sentinel.runtime.execution_kernel import ExecutionKernel, ProjectionCycleContext, MutationTier
    from app.sentinel.topology.project_graph import ProjectTopologyGraph
    from unittest.mock import AsyncMock, patch

    kernel = ExecutionKernel()
    from types import SimpleNamespace
    mock_lease = SimpleNamespace(
        lease_id="test_lease",
        project_id="test_proj",
        holder_id=kernel._kernel_id,
        expires_at=0.0
    )
    
    # Mock LeaseManager, SnapshotManager, and TransactionEngine so we don't hit DB/file-system operations
    with patch("app.sentinel.runtime.leases.LeaseManager.acquire", new_callable=AsyncMock) as mock_acquire, \
         patch("app.sentinel.runtime.leases.LeaseManager.release", new_callable=AsyncMock) as mock_release, \
         patch("app.sentinel.runtime.projection_snapshots.SnapshotManager.create_snapshot", new_callable=AsyncMock) as mock_snapshot, \
         patch("app.sentinel.runtime.transaction_engine.TransactionEngine.begin", new_callable=AsyncMock) as mock_begin, \
         patch("app.sentinel.topology.ast_projector.ASTProjector.project", new_callable=AsyncMock) as mock_project:
        
        mock_acquire.return_value = mock_lease
        
        # Make projector raise a ProjectorError
        mock_project.side_effect = ProjectorError("EMPTY_RESPONSE", "The LLM response was completely empty.")
        
        ctx = ProjectionCycleContext(
            project_id="test_proj",
            project_path=tmp_path,
            mutation_tier=MutationTier.COSMETIC,
            proposed_writes=["src/main.tsx"]
        )
        
        graph = ProjectTopologyGraph(project_id="test_proj")
        
        # We don't want transaction engine rollback/snapshot restore to fail in tests
        with patch("app.sentinel.runtime.transaction_engine.TransactionEngine.rollback", new_callable=AsyncMock), \
             patch("app.sentinel.runtime.projection_snapshots.SnapshotManager.restore_snapshot", new_callable=AsyncMock):
             
            await kernel.run_projection_cycle(
                ctx=ctx,
                graph=graph,
                llm_client=None
            )
            
            # Assertions
            assert ctx.succeeded is False
            assert ctx.verification is not None
            assert ctx.verification.recommendation == "REJECT"
            assert ctx.verification.failure_classification == "PROJECTOR_FAILURE"
            assert len(ctx.verification.failures) == 1
            assert ctx.verification.failures[0].failure_type == "PROJECTOR_FAILURE"
            assert "EMPTY_RESPONSE" in ctx.verification.failures[0].details
