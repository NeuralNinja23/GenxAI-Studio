# app/utils/__init__.py
"""
Utility modules for GenxAI Studio.
"""
from .entity_discovery import (
    discover_primary_entity,
    discover_db_function,
    discover_routers,
    get_entity_plural,
    singularize,
    extract_entity_from_request,
    ENTITY_PATTERNS,
)
from .path_utils import (
    get_project_path,
    get_backend_path,
    get_frontend_path,
    get_backend_app_path,
    get_routers_path,
    get_models_path,
    get_main_py_path,
    get_architecture_path,
    get_tests_path,
    is_valid_project_path,
    ensure_project_directories,
)

__all__ = [
    # Entity Discovery
    "discover_primary_entity",
    "discover_db_function",
    "discover_routers",
    "get_entity_plural",
    "singularize",
    "extract_entity_from_request",
    "ENTITY_PATTERNS",
    # Path Utilities
    "get_project_path",
    "get_backend_path",
    "get_frontend_path",
    "get_backend_app_path",
    "get_routers_path",
    "get_models_path",
    "get_main_py_path",
    "get_architecture_path",
    "get_tests_path",
    "is_valid_project_path",
    "ensure_project_directories",
]


