import pytest
import os
from app.sentinel.topology.import_resolver import ImportResolver

def test_resolve_python():
    # Should strip .py, replace / with ., strip Backend.
    source = "Backend/app/api/routes/customer.py"
    target = "Backend/app/models/customer.py"
    result = ImportResolver.resolve(source, target)
    assert result == "app.models.customer"

def test_resolve_react_alias():
    # Setup alias mode
    ImportResolver.FRONTEND_MODE = "alias"
    
    source = "Frontend/src/pages/Dashboard.tsx"
    target = "Frontend/src/components/CustomerCard.tsx"
    result = ImportResolver.resolve(source, target)
    assert result == "@/components/CustomerCard"
    
def test_resolve_react_alias_fallback_relative():
    ImportResolver.FRONTEND_MODE = "alias"
    
    # Target not in Frontend/src
    source = "Frontend/src/pages/Dashboard.tsx"
    target = "Frontend/components/CustomerCard.tsx"
    result = ImportResolver.resolve(source, target)
    # Should fallback to relative
    # dir: Frontend/src/pages
    # target: Frontend/components/CustomerCard.tsx
    # relpath from Frontend/src/pages to Frontend/components/CustomerCard.tsx
    # -> ../../components/CustomerCard
    assert result == "../../components/CustomerCard"

def test_resolve_react_relative():
    # Setup relative mode
    ImportResolver.FRONTEND_MODE = "relative"
    
    source = "Frontend/src/pages/Dashboard.tsx"
    target = "Frontend/src/components/CustomerCard.tsx"
    result = ImportResolver.resolve(source, target)
    
    # from Frontend/src/pages to Frontend/src/components/CustomerCard.tsx
    # relative: ../components/CustomerCard
    assert result == "../components/CustomerCard"
    
    # Same directory
    source = "Frontend/src/pages/Dashboard.tsx"
    target = "Frontend/src/pages/Settings.tsx"
    result = ImportResolver.resolve(source, target)
    assert result == "./Settings"

def test_empty_paths():
    with pytest.raises(ValueError, match="empty target path"):
        ImportResolver.resolve("source.py", "")
        
    with pytest.raises(ValueError, match="empty source path"):
        ImportResolver.resolve("", "target.py")
