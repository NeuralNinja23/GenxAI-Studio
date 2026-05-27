# app/llm/providers/gemini.py
"""
Google Gemini provider — Vertex AI endpoint with Application Default Credentials (ADC).

Authentication:
    Uses google-auth ADC. Before running the backend, authenticate once with:
        gcloud auth application-default login
        gcloud config set project YOUR_GCP_PROJECT_ID

    In production (Cloud Run / GKE / Compute Engine), ADC is provided automatically
    via the attached service account — no extra configuration required.

Endpoint:
    https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/
        publishers/google/models/{model}:generateContent

Model Names on Vertex AI vs AI Studio:
    AI Studio (old)          Vertex AI (current)
    ----------------------   ---------------------
    gemini-2.0-flash-exp  -> gemini-2.0-flash-001
    gemini-1.5-pro        -> gemini-1.5-pro-002
    gemini-1.5-flash      -> gemini-1.5-flash-002
    gemini-2.5-pro        -> gemini-2.5-pro-preview-05-06
"""

import json
import aiohttp
from typing import Optional

import google.auth
import google.auth.transport.requests

from app.core.config import settings
from app.core.logging import log


# ---------------------------------------------------------------------------
# Model name normalization (AI Studio → Vertex AI stable names)
# ---------------------------------------------------------------------------

_MODEL_MAP = {
    # Gemini 2.5 (latest) — confirmed working on Vertex AI
    # Gemini 3.5 Mapping
    "gemini-3.5-flash":             "gemini-2.5-flash",
    "gemini-3.5-pro":               "gemini-2.5-pro",
    "gemini-2.5-flash":             "gemini-2.5-flash",
    "gemini-2.5-flash-preview-04-17": "gemini-2.5-flash",
    "gemini-2.5-flash-preview-05-20": "gemini-2.5-flash",
    "gemini-2.5-pro":               "gemini-2.5-pro",
    "gemini-2.5-pro-preview-05-06": "gemini-2.5-pro",
    "gemini-2.5-pro-preview-06-05": "gemini-2.5-pro",
    # Gemini 2.0
    "gemini-2.0-flash-exp":         "gemini-2.0-flash-001",
    "gemini-2.0-flash":             "gemini-2.0-flash-001",
    # Gemini 1.5
    "gemini-1.5-pro":               "gemini-1.5-pro-002",
    "gemini-1.5-pro-latest":        "gemini-1.5-pro-002",
    "gemini-1.5-flash":             "gemini-1.5-flash-002",
    "gemini-1.5-flash-latest":      "gemini-1.5-flash-002",
}

DEFAULT_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# ADC credential cache (module-level singleton, thread-safe for asyncio)
# ---------------------------------------------------------------------------

_credentials = None
_adc_project: Optional[str] = None


def _get_credentials():
    """
    Return (refreshed) ADC credentials and the resolved GCP project ID.

    google.auth.default() reads credentials from (in priority order):
      1. GOOGLE_APPLICATION_CREDENTIALS env var (path to service account JSON)
      2. gcloud application-default credentials (~/.config/gcloud/application_default_credentials.json)
      3. Metadata server (Cloud Run, GKE, Compute Engine)
    """
    global _credentials, _adc_project

    if _credentials is None:
        _credentials, discovered_project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        # Prefer explicitly configured project, fall back to ADC-discovered project
        _adc_project = settings.llm.vertex_project_id or discovered_project
        log("Gemini", f"✅ ADC credentials loaded. GCP project: {_adc_project}")

    # Refresh token if expired
    if not _credentials.valid:
        request = google.auth.transport.requests.Request()
        _credentials.refresh(request)

    return _credentials, _adc_project


def _normalize_model(model: Optional[str]) -> str:
    """Map AI Studio model names to Vertex AI stable model names."""
    if not model:
        return DEFAULT_MODEL
    return _MODEL_MAP.get(model, model)


def _build_vertex_url(project_id: str, region: str, model: str) -> str:
    return (
        f"https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}"
        f"/locations/{region}/publishers/google/models/{model}:generateContent"
    )


# ---------------------------------------------------------------------------
# Main call function (same signature as before — drop-in replacement)
# ---------------------------------------------------------------------------

async def call(
    prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8000,
    stop_sequences: Optional[list] = None,
) -> dict:
    """
    Call Google Gemini via Vertex AI using Application Default Credentials.

    Args:
        prompt:          The user-facing prompt text.
        system_prompt:   Optional system instruction.
        model:           Gemini model name (AI Studio or Vertex AI format accepted).
        temperature:     Sampling temperature.
        max_tokens:      Maximum output tokens.
        stop_sequences:  Up to 4 sequences that signal generation completion.

    Returns:
        dict with keys:
            "text"  — the generated text
            "usage" — {"input": int, "output": int, "total": int}

    Raises:
        Exception on authentication or API errors.
    """
    # Resolve credentials and project
    try:
        credentials, project_id = _get_credentials()
    except google.auth.exceptions.DefaultCredentialsError as e:
        raise Exception(
            "Vertex AI ADC not configured. Run: "
            "gcloud auth application-default login"
        ) from e

    if not project_id:
        raise Exception(
            "GCP project not resolved. Set VERTEX_PROJECT_ID in .env or run: "
            "gcloud config set project YOUR_PROJECT_ID"
        )

    region = settings.llm.vertex_region
    vertex_model = _normalize_model(model)
    url = _build_vertex_url(project_id, region, vertex_model)

    log("Gemini", f"→ Vertex AI [{region}] model={vertex_model} tokens={max_tokens}")

    # Build request payload (same structure as AI Studio)
    contents = [{"role": "user", "parts": [{"text": prompt}]}]

    generation_config = {
        "temperature": 0.2,         # Reduced for deterministic code generation
        "maxOutputTokens": max_tokens,
        # NOTE: responseMimeType intentionally omitted — agents output HDAP format, not JSON
    }

    if stop_sequences:
        generation_config["stopSequences"] = stop_sequences[:4]  # Vertex allows max 4

    payload = {
        "contents": contents,
        "generationConfig": generation_config,
    }

    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    # Auth header uses the short-lived bearer token from ADC
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as response:
            text = await response.text()

            if response.status == 429:
                log("Gemini", f"⚠️ 429 Rate limit: {text[:300]}")
                raise Exception(f"Rate limited (429): {text[:200]}")

            if response.status == 403:
                log("Gemini", f"⚠️ 403 Forbidden: {text[:300]}")
                raise Exception(
                    f"Vertex AI permission denied (403). Check that your ADC account has "
                    f"'roles/aiplatform.user' on project '{project_id}': {text[:200]}"
                )

            if response.status == 400:
                log("Gemini", f"⚠️ 400 Bad request: {text[:300]}")
                raise Exception(f"Bad request (400): {text[:200]}")

            if response.status == 404:
                log("Gemini", f"⚠️ 404 Not found — model or project may be wrong: {text[:300]}")
                raise Exception(
                    f"Vertex AI 404 — check model name '{vertex_model}' and "
                    f"project '{project_id}': {text[:200]}"
                )

            if response.status != 200:
                log("Gemini", f"⚠️ Error {response.status}: {text[:300]}")
                raise Exception(f"Vertex AI error {response.status}: {text[:200]}")

            # Parse response (identical structure to AI Studio)
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                log("Gemini", f"⚠️ Failed to parse JSON: {text[:300]}")
                raise Exception(f"Failed to parse Vertex AI response: {e}") from e

            try:
                candidates = data.get("candidates", [])
                if not candidates:
                    raise Exception("No candidates in Vertex AI response")

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    raise Exception("No parts in Vertex AI response")

                text_content = parts[0].get("text", "")

                # Extract token usage for cost tracking
                usage_metadata = data.get("usageMetadata", {})
                usage = {
                    "input":  usage_metadata.get("promptTokenCount", 0),
                    "output": usage_metadata.get("candidatesTokenCount", 0),
                    "total":  usage_metadata.get("totalTokenCount", 0),
                }

                return {
                    "text":  text_content,
                    "usage": usage,
                }

            except (KeyError, IndexError) as e:
                raise Exception(f"Failed to parse Vertex AI response structure: {e}") from e
