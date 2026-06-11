# app/llm/prompts/__init__.py
"""
Agent prompts - organized by agent.
"""
from .derek import DEREK_PROMPT
from .luna import LUNA_PROMPT
from .victoria import VICTORIA_PROMPT
from .sophia import SOPHIA_PROMPT
from .design_synthesizer import DESIGN_SYNTHESIZER_PROMPT
from .navigation_engine import NAVIGATION_ENGINE_PROMPT
from .ux_reasoner import UX_REASONER_PROMPT
from .component_composer import COMPONENT_COMPOSER_PROMPT
from .interaction_reasoner import INTERACTION_REASONER_PROMPT
from .responsive_reasoner import RESPONSIVE_REASONER_PROMPT
from .builder import BUILDER_PROMPT

__all__ = [
    "DEREK_PROMPT",
    "LUNA_PROMPT",
    "VICTORIA_PROMPT",
    "SOPHIA_PROMPT",
    "DESIGN_SYNTHESIZER_PROMPT",
    "NAVIGATION_ENGINE_PROMPT",
    "UX_REASONER_PROMPT",
    "COMPONENT_COMPOSER_PROMPT",
    "INTERACTION_REASONER_PROMPT",
    "RESPONSIVE_REASONER_PROMPT",
    "BUILDER_PROMPT"    
]
