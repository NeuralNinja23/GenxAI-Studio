# app/llm/prompts/design_synthesizer.py
"""
V4 DesignSynthesizer Prompt — Design System Synthesis Faculty

Implements pure cognitive Design Token synthesis.
DesignSynthesizer translates abstract visual temperatures and semantic color intents
from the DesignIntentGraph into precise, framework-agnostic palette characteristics,
typography scales, spacing scale types, and motion timings.
The synthesizer is strictly prohibited from generating HSL coordinates, hex values,
physical visual styles, or direct frontend components.
"""

DESIGN_SYNTHESIZER_PROMPT = """
You are the Design System Synthesis Faculty of GenxAI Studio.
Your role is to translate abstract cognitive UX intents (from the DesignIntentGraph) and product ontology schemas
into a framework-agnostic Design System.

🚨 COLOR PALETTE CHARACTERISTICS (Choose abstract metrics, NEVER physical colors/hexes):
- stability: "High stability" | "Expressive variance" | "Low variance"
- saturation_variance: "Low saturation variance" | "High saturation variance"
- readability_demands: "High readability" | "Normal readability"
- temperature_profile: "Cold Slate" | "Warm Organic" | "High Dynamic Range" | "Monochromatic tone curves"

🚨 TYPOGRAPHY SCALES (Choose abstract size categories):
- Sans-Serif font family category (e.g. "Sans-Inter", "Sans-Outfit")
- Monospace font family category (e.g. "Mono-Roboto", "Mono-Fira")
- font_scale categories (list of labels representing size, e.g. ["xs", "sm", "base", "lg", "xl"])

🚨 SPACING SCALE PARADIGMS (Choose based on complexity and focus intents):
- spacing_scale_type: "Utility Dense" (for power-user analytic screens) | "Comfortable Layout" | "Spacious Focus"
- border_radius_type: "Sharp Geometric" | "Standard Rounded" | "Soft Pill"
- shadow_density: "Low Outline" | "Standard Soft" | "High Depth"

🚨 MOTION SCALES:
- duration_speed: "Instant" (no transitions) | "Snappy" (fast visual feedback, e.g. 150ms) | "Fluid" (deliberate motion, e.g. 300ms)
- easing_type: "Linear" | "Standard Easing" | "Accelerate Easing"

🚨 COMPONENT RULES:
- focus_outline_style: "Double Outline Rings" | "High Contrast Solid Outline" | "Subtle Ring"
- border_width_profile: "Hairline Solid" | "Thick Outline"

Input Product Ontology Graph:
{ontology_graph_json}

Input Design Intent Graph:
{design_intent_graph_json}

Produce a valid JSON object matching this schema exactly:
{{
  "design_system": {{
    "theme_name": "Precision Analytical Theme",
    "base_ratio": 1.25,
    "color_characteristics": {{
      "stability": "High stability",
      "saturation_variance": "Low saturation variance",
      "readability_demands": "High readability",
      "temperature_profile": "Monochromatic tone curves"
    }},
    "typography": {{
      "font_family_sans": "Sans-Inter",
      "font_family_mono": "Mono-Fira",
      "font_scale": ["xs", "sm", "base", "lg", "xl"]
    }},
    "spacing": {{
      "spacing_scale_type": "Utility Dense",
      "border_radius_type": "Sharp Geometric",
      "shadow_density": "Low Outline"
    }},
    "motion": {{
      "duration_speed": "Snappy",
      "easing_type": "Standard Easing"
    }},
    "component_rules": {{
      "focus_outline_style": "Double Outline Rings",
      "border_width_profile": "Hairline Solid"
    }}
  }}
}}

⚠️ CRITICAL RULES:
1. DO NOT invent/emit hex codes, RGB coordinates, HSL integers, or concrete CSS variables (like "16px").
2. Follow cognitive constraints strictly. Do not specify loose, spacious spacing scales ("Spacious Focus") if the parent intent requested maximizing utility.

Generate ONLY valid JSON without markdown wrapping.
"""
