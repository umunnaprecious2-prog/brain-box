import json
import logging
import re

import httpx
from openai import OpenAI

from app.config.settings import OPENAI_API_KEY, PROXY_URL

logger = logging.getLogger(__name__)

_http_client = httpx.Client(proxy=PROXY_URL) if PROXY_URL else None
_client = OpenAI(api_key=OPENAI_API_KEY, http_client=_http_client)

RESTRUCTURE_PROMPT = (
    "You are a content restructuring assistant for a GitHub-based knowledge archive.\n"
    "Given a piece of content and its metadata, return a JSON object with exactly "
    "these fields:\n"
    '- "markdown": the content restructured as clean, readable Markdown. '
    "Include a title heading, the summary, tags as badges, and the original content "
    "formatted clearly.\n"
    '- "suggested_subfolder": a short lowercase folder name for organizing by topic '
    '(e.g., "finance", "technology", "recipes"). Use only alphanumeric and hyphens.\n'
    '- "suggested_filename": a short, descriptive filename ending in .md '
    '(e.g., "investment-basics.md"). Use only lowercase, hyphens, and alphanumeric.\n'
    '- "commit_message": a concise commit message describing what is being added '
    '(e.g., "Add notes on investment basics").\n\n'
    "Return ONLY valid JSON. No markdown fences, no extra text."
)


def restructure_for_github(
    text: str,
    content_type: str,
    original_name: str,
    tags: list[str],
    summary: str,
    topic: str,
) -> dict:
    """Use AI to restructure content into Markdown and suggest GitHub paths.

    Returns dict with keys: markdown, suggested_subfolder,
    suggested_filename, commit_message.
    """
    if not text or not text.strip():
        return _fallback_result(content_type, original_name, tags, summary, topic)

    truncated = text[:3000]
    user_message = (
        f"Content type: {content_type}\n"
        f"Original name: {original_name}\n"
        f"Tags: {', '.join(tags)}\n"
        f"Summary: {summary}\n"
        f"Topic: {topic}\n\n"
        f"Content:\n{truncated}"
    )

    try:
        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": RESTRUCTURE_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1500,
        )

        raw = response.choices[0].message.content or ""
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()

        result = json.loads(raw)
        return _validate_result(result, content_type, original_name, tags, summary)

    except json.JSONDecodeError:
        logger.warning("OpenAI returned non-JSON for restructuring.")
        return _fallback_result(content_type, original_name, tags, summary, topic)
    except Exception:
        logger.exception("OpenAI restructuring call failed.")
        return _fallback_result(content_type, original_name, tags, summary, topic)


def _validate_result(
    result: dict,
    content_type: str,
    original_name: str,
    tags: list[str],
    summary: str,
) -> dict:
    """Validate and sanitize AI output deterministically."""
    markdown = result.get("markdown", "")
    if not isinstance(markdown, str) or not markdown.strip():
        markdown = _build_default_markdown(original_name, tags, summary)

    subfolder = result.get("suggested_subfolder", "general")
    if not isinstance(subfolder, str) or not subfolder.strip():
        subfolder = "general"
    subfolder = re.sub(r"[^a-z0-9-]", "-", subfolder.lower().strip())[:50]

    filename = result.get("suggested_filename", "")
    if not isinstance(filename, str) or not filename.strip():
        safe_name = re.sub(r"[^a-z0-9-]", "-", original_name.lower())[:40]
        filename = f"{safe_name}.md"
    filename = re.sub(r"[^a-z0-9.\-]", "-", filename.lower().strip())[:60]
    if not filename.endswith(".md"):
        filename = filename.rsplit(".", 1)[0] + ".md"

    commit_msg = result.get("commit_message", "")
    if not isinstance(commit_msg, str) or not commit_msg.strip():
        commit_msg = f"Add {content_type}: {original_name}"
    commit_msg = commit_msg[:120]

    return {
        "markdown": markdown,
        "suggested_subfolder": subfolder,
        "suggested_filename": filename,
        "commit_message": commit_msg,
    }


def _fallback_result(
    content_type: str,
    original_name: str,
    tags: list[str],
    summary: str,
    topic: str,
) -> dict:
    """Deterministic fallback when AI is unavailable."""
    safe_name = re.sub(r"[^a-z0-9-]", "-", original_name.lower())[:40]
    return {
        "markdown": _build_default_markdown(original_name, tags, summary),
        "suggested_subfolder": topic or "general",
        "suggested_filename": f"{safe_name}.md",
        "commit_message": f"Add {content_type}: {original_name}",
    }


def _build_default_markdown(original_name: str, tags: list[str], summary: str) -> str:
    tag_line = " ".join(f"`{t}`" for t in tags) if tags else ""
    return (
        f"# {original_name}\n\n" f"**Summary:** {summary}\n\n" f"**Tags:** {tag_line}\n"
    )
