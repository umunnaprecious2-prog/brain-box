import logging
from io import BytesIO
from pathlib import Path

import httpx
import pdfplumber
from bs4 import BeautifulSoup
from docx import Document as DocxDocument

from app.config.settings import PROXY_URL

logger = logging.getLogger(__name__)


def extract_text_from_pdf(data: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(data: bytes) -> str:
    doc = DocxDocument(BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_url(url: str) -> str:
    try:
        response = httpx.get(url, timeout=15, follow_redirects=True, proxy=PROXY_URL)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Failed to fetch URL: %s", url)
        return ""

    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Truncate to avoid excessively large texts
    return text[:5000]


def extract_text(
    content_type: str, data: bytes | None = None, url: str | None = None
) -> str:
    if content_type == "documents" and data:
        # Try PDF first, then DOCX
        try:
            return extract_text_from_pdf(data)
        except Exception:
            pass
        try:
            return extract_text_from_docx(data)
        except Exception:
            logger.warning("Could not extract text from document.")
            return ""
    elif content_type == "links" and url:
        return extract_text_from_url(url)
    elif content_type == "images":
        return ""  # Image text extraction not in v1 scope
    elif content_type == "notes":
        if data:
            return data.decode("utf-8", errors="replace")
        return ""
    return ""


def detect_content_type(filename: str | None, mime_type: str | None) -> str:
    if mime_type:
        if mime_type.startswith("image/"):
            return "images"
        if mime_type in (
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return "documents"

    if filename:
        ext = Path(filename).suffix.lower()
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"):
            return "images"
        if ext in (".pdf", ".docx", ".doc"):
            return "documents"

    return "notes"
