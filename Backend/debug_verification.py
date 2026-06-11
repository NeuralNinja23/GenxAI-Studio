import sys
from pathlib import Path
import tempfile
import shutil

# Add backend directory to path
sys.path.insert(0, str(Path("c:/Users/JARVIS/Desktop/GenxAI Labz/GenxAI Studio/GenxAI Studio V4/backend")))

from app.studio.architecture.workspace_architecture import WorkspaceArchitecture
from app.sentinel.verification.verification_gate import SentinelVerificationGate
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType

with tempfile.TemporaryDirectory() as tmp_dir:
    project_path = Path(tmp_dir)
    components_dir = project_path / "Frontend" / "src" / "components"
    components_dir.mkdir(parents=True)
    with open(components_dir / "Form.tsx", "w", encoding="utf-8") as f:
        f.write("export default function Form() { return <button onClick={customSubmitHandler}>Submit</button>; }")
    graph = ProjectTopologyGraph(project_id="state_test")
    graph.add_node("ui_form", NodeType.UI_NODE, {"is_root": True})
    graph.update_graph_hash()
    res = SentinelVerificationGate.verify(project_path, graph)
    print("STATE BINDINGS RESULT:")
    print("failures:", res.failures)
    print("warnings:", res.warnings)
