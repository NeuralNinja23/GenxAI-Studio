# app/substrate/__init__.py
"""V4 Substrate Package — Stable execution substrate management."""
from .substrate_manager import SubstrateManager, LOCKED_SUBSTRATE_FILES, FORBIDDEN_WRITE_TARGETS

__all__ = ["SubstrateManager", "LOCKED_SUBSTRATE_FILES", "FORBIDDEN_WRITE_TARGETS"]
