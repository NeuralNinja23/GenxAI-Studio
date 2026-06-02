import asyncio
from pathlib import Path
from app.orchestration.sentinel_runtime import SentinelRuntime
from app.db import connect_db, disconnect_db

async def main():
    project_id = "test_project_id"
    workspaces_path = Path("C:/Users/JARVIS/Desktop/GenxAI Labz/GenxAI Studio/GenxAI Studio V4/workspaces")
    
    print("Starting direct runtime test...")
    try:
        await connect_db()
        runtime = SentinelRuntime()
        success = await runtime.explore_and_project(
            project_id=project_id,
            project_path=workspaces_path / project_id,
            user_request="Test App"
        )
        print(f"Runtime finished. Success: {success}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Runtime failed with exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
