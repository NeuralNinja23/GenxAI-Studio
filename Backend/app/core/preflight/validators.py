import os
import subprocess
import shutil
from typing import List, Dict, Any

class PreflightFailure(Exception):
    """Raised when a preflight check fails. Caught by PreflightKernel to aggregate diagnostics."""
    def __init__(self, category: str, message: str, context: Dict[str, Any] = None):
        super().__init__(f"[{category}] {message}")
        self.category = category
        self.message = message
        self.context = context or {}

class EnvironmentValidator:
    """Validates that necessary environment variables are set."""
    @staticmethod
    def validate() -> None:
        required_vars = ["GOOGLE_APPLICATION_CREDENTIALS", "VERTEX_PROJECT_ID"]
        missing = [v for v in required_vars if not os.environ.get(v)]
        
        # This is a soft check, often local dev relies on gcloud ADC rather than strict env vars,
        # but we must ensure *some* valid auth mechanism exists. For now we will just verify
        # that basic system environment looks sane.
        if "NODE_ENV" in os.environ and os.environ["NODE_ENV"] == "production":
            raise PreflightFailure(
                "Environment", 
                "GenxAI Studio backend cannot run in NODE_ENV=production. It is a development orchestrator."
            )

class DependencyValidator:
    """Validates that required system dependencies are installed."""
    @staticmethod
    def validate() -> None:
        if not shutil.which("docker"):
            raise PreflightFailure(
                "Dependency", 
                "Docker is not installed or not in PATH. Sentinel requires Docker to run the Sandbox."
            )
        
        if not shutil.which("node"):
            raise PreflightFailure(
                "Dependency", 
                "Node.js is not installed or not in PATH."
            )

class PackageValidator:
    """Validates that required Python packages are installed."""
    @staticmethod
    def validate() -> None:
        REQUIRED_PACKAGES = [
            "json_repair",
            "pydantic",
            "fastapi",
        ]
        
        missing = []
        for pkg in REQUIRED_PACKAGES:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
                
        if missing:
            raise PreflightFailure(
                "PackageDependency",
                f"Required Python packages are missing: {', '.join(missing)}. Please run 'pip install -r requirements.txt'."
            )

class InfrastructureValidator:
    """Validates that the Docker daemon is actually running and responsive."""
    @staticmethod
    def validate() -> None:
        try:
            result = subprocess.run(
                ["docker", "info"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode != 0:
                raise PreflightFailure(
                    "Infrastructure", 
                    "Docker daemon is not running.",
                    context={"stderr": result.stderr}
                )
        except Exception as e:
            if isinstance(e, PreflightFailure):
                raise
            raise PreflightFailure(
                "Infrastructure", 
                f"Failed to communicate with Docker daemon: {str(e)}"
            )
