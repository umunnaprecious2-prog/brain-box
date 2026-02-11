import json
import logging

import httpx
from openai import OpenAI

from app.config.settings import OPENAI_API_KEY, PROXY_URL

logger = logging.getLogger(__name__)

_http_client = httpx.Client(proxy=PROXY_URL) if PROXY_URL else None
_client = OpenAI(api_key=OPENAI_API_KEY, http_client=_http_client)

SYSTEM_PROMPT = (
    "You are a content classification assistant. "
    "Given a piece of text, return a JSON object with exactly these fields:\n"
    '- "tags": a list of 3-5 relevant keyword tags (lowercase strings)\n'
    '- "summary": a 1-2 sentence summary of the content\n'
    '- "topic": a single lowercase topic category word '
    '(e.g., "finance", "technology", "health", "education", '
    '"personal", "work", "general")\n\n'
    "Return ONLY valid JSON. No markdown, no extra text."
)


def analyze_content(text: str, content_type: str) -> dict:
    if not text or not text.strip():
        return {
            "tags": [content_type],
            "summary": "No text content available for analysis.",
            "topic": "general",
        }

    # Truncate very long text to stay within token limits
    truncated = text[:3000]

    try:
        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Content type: {content_type}\n\nText:\n{truncated}",
                },
            ],
            temperature=0.3,
            max_tokens=300,
        )

        raw = response.choices[0].message.content or ""
        # Strip potential markdown fences
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()

        result = json.loads(raw)

        # Validate structure
        tags = result.get("tags", [content_type])
        if not isinstance(tags, list):
            tags = [content_type]

        summary = result.get("summary", "")
        if not isinstance(summary, str) or not summary:
            summary = "No summary generated."

        topic = result.get("topic", "general")
        if not isinstance(topic, str) or not topic:
            topic = "general"

        return {
            "tags": [str(t).lower().strip() for t in tags[:5]],
            "summary": summary[:500],
            "topic": topic.lower().strip(),
        }

    except json.JSONDecodeError:
        logger.warning("OpenAI returned non-JSON response.")
        return {
            "tags": [content_type],
            "summary": "AI analysis failed — content stored without summary.",
            "topic": "general",
        }
    except Exception:
        logger.exception("OpenAI API call failed.")
        return {
            "tags": [content_type],
            "summary": "AI analysis failed — content stored without summary.",
            "topic": "general",
        }
