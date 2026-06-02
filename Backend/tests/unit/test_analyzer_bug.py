from app.sentinel.topology.ast_projector import ASTProjector
from app.sentinel.verification.verification_gate import FailureFingerprint
from app.sentinel.failure_memory.failure_analyzer import FailureAnalyzer
from app.sentinel.telemetry.validation_bus import ValidationBus

def run_test():
    failures = [
        FailureFingerprint(
            failure_type="TOPOLOGY_INTEGRITY_FAILURE",
            stage="Verification Layer F",
            details="Orphaned Module: UI component 'ui_task_item' is structurally unreachable from primary AppLayout/Dashboard."
        ),
        FailureFingerprint(
            failure_type="RUNTIME_BOOT_FAILURE",
            stage="Layer E: Static Runtime Health",
            details="App entry does not expose a component with a JSX render path."
        ),
        FailureFingerprint(
            failure_type="FRONTEND_BUILD_FAILURE",
            stage="Verification Layer D",
            details="Frontend structural build error: Unbalanced tags inside TSX components"
        )
    ]

    try:
        FailureAnalyzer.analyze_and_record(failures)
        print("Analyze successful!")
        events = ValidationBus().get_events()
        for e in events:
            print(e["type"], e["payload"].get("cluster_id") or e["payload"].get("cascade_id"))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
