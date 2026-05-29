# tests/unit/test_patch_ir_normalizer.py
"""
Unit tests for the PatchIRNormalizer defensive layer.
"""

import pytest
from app.sentinel.cognition.patch_ir_normalizer import PatchIRNormalizer
from app.models.runtime_models import MutationTier


def test_normalizer_canonicalizes_ids():
    raw_patches = [
        {
            "patch_id": " VIC-UI-1  ",
            "target_node_id": " UI_KanbanBoard ",
            "mutation_tier": "structural_ui",
            "action": "add_node",
            "node_data": {
                "node_type": "UI_NODE",
                "properties": {
                    "component_name": "KanbanBoard"
                }
            }
        }
    ]

    normalized = PatchIRNormalizer.normalize_patch_list(raw_patches)
    assert len(normalized) == 1
    patch = normalized[0]
    assert patch.patch_id == "vic-ui-1"
    assert patch.target_node_id == "ui_kanbanboard"
    assert patch.action == "ADD_NODE"
    assert patch.mutation_tier == MutationTier.STRUCTURAL_UI


def test_normalizer_normalizes_relationships():
    raw_patches = [
        {
            "patch_id": "edge-1",
            "target_node_id": "edge-1",
            "action": "ADD_EDGE",
            "edge_data": {
                "source": "UI_Dashboard",
                "target": "API_Tasks",
                "relation": "routes_to_api"
            }
        }
    ]

    normalized = PatchIRNormalizer.normalize_patch_list(raw_patches)
    assert len(normalized) == 1
    edge = normalized[0].edge_data
    assert edge["source"] == "ui_dashboard"
    assert edge["target"] == "api_tasks"
    assert edge["relation"] == "routes_to"


def test_normalizer_rejects_invalid_actions():
    raw_patches = [
        {
            "patch_id": "patch-invalid",
            "target_node_id": "node",
            "action": "MUTATE_DIRECTLY"
        }
    ]
    normalized = PatchIRNormalizer.normalize_patch_list(raw_patches)
    assert len(normalized) == 0


def test_normalizer_deduplicates_patch_ids():
    raw_patches = [
        {
            "patch_id": "patch-1",
            "target_node_id": "node-1",
            "action": "ADD_NODE"
        },
        {
            "patch_id": "patch-1",
            "target_node_id": "node-2",
            "action": "ADD_NODE"
        }
    ]
    normalized = PatchIRNormalizer.normalize_patch_list(raw_patches)
    assert len(normalized) == 1
    assert normalized[0].target_node_id == "node-1"


def test_normalizer_handles_markdown_json_string():
    raw_string = """
    ```json
    [
      {
        "patch_id": "string-patch",
        "target_node_id": "string-node",
        "action": "ADD_NODE"
      }
    ]
    ```
    """
    normalized = PatchIRNormalizer.normalize_patch_list(raw_string)
    assert len(normalized) == 1
    assert normalized[0].patch_id == "string-patch"
