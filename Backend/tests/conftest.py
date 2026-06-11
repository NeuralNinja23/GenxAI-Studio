# tests/conftest.py
import pytest
from app.core.config import settings

@pytest.fixture(autouse=True)
def disable_strict_governance_for_unit_tests():
    """
    Ensures unit tests default to strict_workspace_governance = False.
    This prevents legacy test fixtures (which use 'Frontend'/'Backend' casing)
    from triggering casing violations. Architecture tests will patch this to True.
    """
    settings.strict_workspace_governance = False
