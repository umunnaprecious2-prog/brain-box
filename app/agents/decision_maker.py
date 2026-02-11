import json
import logging

import httpx
from openai import OpenAI

from app.config.settings import OPENAI_API_KEY, PROXY_URL

logger = logging.getLogger(__name__)

_http_client = httpx.Client(proxy=PROXY_URL) if PROXY_URL else None
_client = OpenAI(api_key=OPENAI_API_KEY, http_client=_http_client)

DECISION_PROMPT = (
    "You are a decision support assistant for a knowledge management system.\n"
    "Given a decision context, analyze it and return a JSON object with exactly "
    "these fields:\n"
    '- "recommendation": the recommended action (e.g., "publish_to_github", '
    '"store_locally_only")\n'
    '- "rationale": a clear explanation of why this recommendation makes sense '
    "(2-3 sentences)\n"
    '- "confidence": one of "high", "medium", or "low"\n\n'
    "Return ONLY valid JSON. No markdown fences, no extra text."
)


def make_publish_decision(
    content_type: str,
    has_trigger: bool,
    tags: list[str],
    summary: str,
    topic: str,
) -> dict:
    """Use AI to generate a decision recommendation about publishing to GitHub.

    Returns dict with keys: recommendation, rationale, confidence.
    AI generates the text, but the application controls persistence.
    """
    # Build context for the decision
    options = [
        "publish_to_github: Restructure content and push to GitHub repository",
        "store_locally_only: Keep content in local storage without publishing",
    ]

    context_text = (
        f"Content type: {content_type}\n"
        f"Has explicit publish trigger (#github or /publish): {has_trigger}\n"
        f"Tags: {', '.join(tags)}\n"
        f"Summary: {summary}\n"
        f"Topic: {topic}\n\n"
        f"Available options:\n"
    )
    for option in options:
        context_text += f"- {option}\n"

    try:
        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": DECISION_PROMPT},
                {"role": "user", "content": context_text},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        raw = response.choices[0].message.content or ""
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()

        result = json.loads(raw)
        return _validate_decision(result, has_trigger)

    except json.JSONDecodeError:
        logger.warning("OpenAI returned non-JSON for decision making.")
        return _fallback_decision(has_trigger)
    except Exception:
        logger.exception("OpenAI decision call failed.")
        return _fallback_decision(has_trigger)


def _validate_decision(result: dict, has_trigger: bool) -> dict:
    """Validate and sanitize AI decision output."""
    recommendation = result.get("recommendation", "")
    if not isinstance(recommendation, str) or recommendation not in (
        "publish_to_github",
        "store_locally_only",
    ):
        recommendation = "publish_to_github" if has_trigger else "store_locally_only"

    rationale = result.get("rationale", "")
    if not isinstance(rationale, str) or not rationale.strip():
        rationale = _generate_default_rationale(recommendation, has_trigger)

    confidence = result.get("confidence", "")
    if not isinstance(confidence, str) or confidence not in ("high", "medium", "low"):
        confidence = "high" if has_trigger else "medium"

    return {
        "recommendation": recommendation,
        "rationale": rationale,
        "confidence": confidence,
    }


def _fallback_decision(has_trigger: bool) -> dict:
    """Deterministic fallback when AI is unavailable."""
    if has_trigger:
        return {
            "recommendation": "publish_to_github",
            "rationale": (
                "Explicit publish trigger detected. "
                "User requested GitHub publishing."
            ),
            "confidence": "high",
        }
    else:
        return {
            "recommendation": "store_locally_only",
            "rationale": "No publish trigger present. Content stored locally only.",
            "confidence": "high",
        }


def _generate_default_rationale(recommendation: str, has_trigger: bool) -> str:
    """Generate a default rationale based on the recommendation."""
    if recommendation == "publish_to_github":
        if has_trigger:
            return (
                "Explicit publish trigger detected. User requested GitHub publishing."
            )
        else:
            return "Content appears suitable for public knowledge sharing via GitHub."
    else:
        return "No publish trigger present. Content stored locally only."
