import sys
from typing import List
from app.core.logging import log
from .validators import (
    EnvironmentValidator,
    DependencyValidator,
    InfrastructureValidator,
    PreflightFailure
)

class PreflightKernel:
    """
    The Runtime Integrity Kernel.
    Executes all preflight validators before ArborMind is allowed to boot.
    Aggregates failures into a categorized diagnostic report rather than crashing instantly.
    """
    
    @staticmethod
    def boot() -> None:
        log("PREFLIGHT", "🚀 Booting Preflight Kernel... validating host integrity.")
        
        failures: List[PreflightFailure] = []
        
        validators = [
            EnvironmentValidator.validate,
            DependencyValidator.validate,
            InfrastructureValidator.validate
        ]
        
        for validate_fn in validators:
            try:
                validate_fn()
            except PreflightFailure as e:
                failures.append(e)
            except Exception as e:
                failures.append(PreflightFailure("Unknown", f"Unexpected validation error: {str(e)}"))
                
        if failures:
            log("PREFLIGHT", f"❌ Preflight Kernel blocked boot due to {len(failures)} integrity failure(s):")
            
            # Group diagnostics by category
            categories = {}
            for f in failures:
                categories.setdefault(f.category, []).append(f)
                
            for category, errs in categories.items():
                print(f"\n[{category.upper()} FAILURES]")
                for err in errs:
                    print(f"  - {err.message}")
                    if err.context:
                        print(f"    Context: {err.context}")
                        
            print("\nArborMind cannot guarantee deterministic execution in a compromised environment.")
            sys.exit(1)
            
        log("PREFLIGHT", "✅ Host integrity verified. Kernel boot complete.")
