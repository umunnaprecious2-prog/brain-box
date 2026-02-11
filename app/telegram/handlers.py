import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from app.agents.aggregation import detect_content_type, extract_text
from app.agents.content_restructurer import restructure_for_github
from app.agents.decision_maker import make_publish_decision
from app.agents.github_publisher import (
    CONTENT_TYPE_TO_GITHUB_FOLDER,
    ensure_repo_folders,
    publish_binary_content,
    publish_text_content,
)
from app.agents.organization import analyze_content
from app.config.settings import TELEGRAM_ALLOWED_USER_ID
from app.database import repository as db
from app.storage.file_storage import save_file, save_text_content

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"https?://[^\s]+")
GITHUB_TRIGGER_PATTERN = re.compile(r"#github\b", re.IGNORECASE)


def _is_authorized(user_id: int) -> bool:
    return user_id == TELEGRAM_ALLOWED_USER_ID


async def _reject_unauthorized(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Access denied. You are not authorized to use this bot."
        )


def _has_publish_trigger(text: str | None) -> bool:
    """Check if the message text contains a #github publish trigger."""
    if not text:
        return False
    return bool(GITHUB_TRIGGER_PATTERN.search(text))


async def _make_and_persist_decision(
    content_type: str,
    has_trigger: bool,
    ai_result: dict,
    item_id: int,
    telegram_message_id: int,
) -> dict:
    """Generate a publish decision using AI and persist it to the database.

    AI generates recommendation, rationale, and confidence.
    Application controls persistence.
    Returns the decision dict.
    """
    # AI generates decision recommendation
    decision = await asyncio.to_thread(
        make_publish_decision,
        content_type=content_type,
        has_trigger=has_trigger,
        tags=ai_result["tags"],
        summary=ai_result["summary"],
        topic=ai_result["topic"],
    )

    # Application persists decision to database
    options_text = (
        "1. publish_to_github: Restructure content and push to GitHub\n"
        "2. store_locally_only: Keep in local storage only"
    )
    context_text = (
        f"Content type: {content_type}\n"
        f"Has trigger: {has_trigger}\n"
        f"Tags: {', '.join(ai_result['tags'])}\n"
        f"Summary: {ai_result['summary']}\n"
        f"Topic: {ai_result['topic']}"
    )

    await asyncio.to_thread(
        db.save_decision,
        decision_name="github_publish_decision",
        context=context_text,
        options=options_text,
        recommendation=decision["recommendation"],
        rationale=decision["rationale"],
        confidence=decision["confidence"],
        content_item_id=item_id,
        telegram_message_id=telegram_message_id,
    )

    return decision


async def _publish_to_github(
    content_type: str,
    original_name: str,
    text: str,
    raw_bytes: bytes | None,
    ai_result: dict,
    item_id: int,
    message,
) -> None:
    """Restructure content with AI, then publish to GitHub via the publisher agent.

    AI: restructure + suggest paths/filenames/commit messages.
    Application: create folders, write files, commit, push.
    """
    try:
        await message.reply_text("Publishing to GitHub...")

        # AI restructures content and suggests paths
        restructured = await asyncio.to_thread(
            restructure_for_github,
            text=text,
            content_type=content_type,
            original_name=original_name,
            tags=ai_result["tags"],
            summary=ai_result["summary"],
            topic=ai_result["topic"],
        )

        # Application determines the GitHub folder
        github_folder = CONTENT_TYPE_TO_GITHUB_FOLDER.get(content_type, "notes")
        folder_path = f"{github_folder}/{restructured['suggested_subfolder']}"

        # Application ensures repo folders exist
        await asyncio.to_thread(ensure_repo_folders)

        # Application publishes the restructured markdown
        github_url = await asyncio.to_thread(
            publish_text_content,
            folder_path=folder_path,
            filename=restructured["suggested_filename"],
            content=restructured["markdown"],
            commit_message=restructured["commit_message"],
        )

        # For binary content (images, PDFs), also publish the raw file
        if raw_bytes and content_type in ("images", "documents"):
            await asyncio.to_thread(
                publish_binary_content,
                folder_path=folder_path,
                filename=original_name,
                data=raw_bytes,
                commit_message=f"Add raw file: {original_name}",
            )

        # Application updates database with GitHub status
        await asyncio.to_thread(db.update_github_status, item_id, github_url)

        await message.reply_text(f"Published to GitHub: {github_url}")

    except Exception:
        logger.exception("GitHub publishing failed for item %s", item_id)
        await message.reply_text("GitHub publishing failed. Content is saved locally.")


# ── /start ──────────────────────────────────────────────────────────────────


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    await update.effective_message.reply_text(  # type: ignore[union-attr]
        "Welcome to Brain Box!\n\n"
        "Send me documents, images, links, or text and I'll organize them for you.\n\n"
        "Commands:\n"
        "/list <type> — Show items (images, documents, links, notes)\n"
        "/search <keyword> — Search your knowledge base\n"
        "/date <YYYY-MM-DD> — Filter by date\n"
        "/publish — Publish latest item to GitHub\n"
        "/help — Show this message\n\n"
        "Add #github to any message to auto-publish to GitHub."
    )


# ── /help ───────────────────────────────────────────────────────────────────


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    await update.effective_message.reply_text(  # type: ignore[union-attr]
        "Brain Box — Your personal knowledge assistant\n\n"
        "Just send me any content:\n"
        "  - PDF / DOCX documents\n"
        "  - Images\n"
        "  - Links (URLs)\n"
        "  - Text notes\n\n"
        "Commands:\n"
        "/list images — Show all images\n"
        "/list documents — Show all documents\n"
        "/list links — Show all links\n"
        "/list notes — Show all notes\n"
        "/search <keyword> — Keyword search\n"
        "/date <YYYY-MM-DD> — Filter by date\n"
        "/publish — Publish latest unpublished item to GitHub\n\n"
        "GitHub Publishing:\n"
        "  Add #github to any message or caption to auto-publish.\n"
        "  Use /publish to publish the most recent unpublished item."
    )


# ── /list ───────────────────────────────────────────────────────────────────


async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    if not context.args:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "Usage: /list <type>\nTypes: images, documents, links, notes"
        )
        return

    content_type = context.args[0].lower()
    if content_type not in ("images", "documents", "links", "notes"):
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "Invalid type. Choose from: images, documents, links, notes"
        )
        return

    items = db.list_by_content_type(content_type)
    if not items:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"No {content_type} found."
        )
        return

    lines = [f"Your {content_type} ({len(items)} items):\n"]
    for item in items[:20]:  # Limit to 20 items in response
        tags = item.tags or "—"
        summary = item.summary or "—"
        gh_status = " [GH]" if item.github_published else ""
        lines.append(
            f"• {item.original_name}{gh_status}\n"
            f"  Tags: {tags}\n"
            f"  Summary: {summary}\n"
        )

    await update.effective_message.reply_text("\n".join(lines))  # type: ignore[union-attr]


# ── /search ─────────────────────────────────────────────────────────────────


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    if not context.args:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "Usage: /search <keyword>"
        )
        return

    keyword = " ".join(context.args)
    items = db.search_by_keyword(keyword)

    if not items:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f'No results for "{keyword}".'
        )
        return

    lines = [f'Search results for "{keyword}" ({len(items)} items):\n']
    for item in items[:20]:
        lines.append(
            f"• [{item.content_type}] {item.original_name}\n"
            f"  Tags: {item.tags or '—'}\n"
        )

    await update.effective_message.reply_text("\n".join(lines))  # type: ignore[union-attr]


# ── /date ───────────────────────────────────────────────────────────────────


async def date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    if not context.args:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "Usage: /date <YYYY-MM-DD>"
        )
        return

    try:
        target_date = datetime.strptime(context.args[0], "%Y-%m-%d").date()
    except ValueError:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "Invalid date format. Use YYYY-MM-DD."
        )
        return

    items = db.filter_by_date(target_date)

    if not items:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"No items found for {target_date}."
        )
        return

    lines = [f"Items from {target_date} ({len(items)} items):\n"]
    for item in items[:20]:
        lines.append(
            f"• [{item.content_type}] {item.original_name}\n"
            f"  Tags: {item.tags or '—'}\n"
        )

    await update.effective_message.reply_text("\n".join(lines))  # type: ignore[union-attr]


# ── /publish ────────────────────────────────────────────────────────────────


async def publish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publish the most recent unpublished item to GitHub."""
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    message = update.effective_message
    if not message:
        return

    items = await asyncio.to_thread(db.get_latest_unpublished)
    if not items:
        await message.reply_text("No unpublished items found.")
        return

    item = items[0]

    # Read the stored file content for AI restructuring
    text = ""
    raw_bytes = None
    file_path = Path(item.file_path)
    if file_path.exists():
        raw_bytes = file_path.read_bytes()
        if item.content_type in ("notes", "links"):
            text = raw_bytes.decode("utf-8", errors="replace")
        elif item.content_type == "documents":
            text = await asyncio.to_thread(extract_text, item.content_type, raw_bytes)
        elif item.content_type == "images":
            text = item.summary or ""
    else:
        text = item.summary or ""

    ai_result = {
        "tags": (item.tags or "").split(", "),
        "summary": item.summary or "",
        "topic": item.topic or "general",
    }

    await _publish_to_github(
        content_type=item.content_type,
        original_name=item.original_name,
        text=text,
        raw_bytes=raw_bytes,
        ai_result=ai_result,
        item_id=item.id,
        message=message,
    )


# ── Document handler ────────────────────────────────────────────────────────


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    message = update.effective_message
    if not message or not message.document:
        return

    doc = message.document
    original_name = doc.file_name or "unnamed_document"
    content_type = detect_content_type(original_name, doc.mime_type)

    # Check for publish trigger in caption
    should_publish = _has_publish_trigger(message.caption)

    await message.reply_text(f"Received {content_type}: {original_name}\nProcessing...")

    try:
        # Step 1: Download raw file
        tg_file = await doc.get_file()
        data = await tg_file.download_as_bytearray()
        raw_bytes = bytes(data)

        # Step 2: Save raw file to disk BEFORE AI processing
        file_path = await asyncio.to_thread(
            save_file,
            content_type=content_type,
            topic="general",
            telegram_message_id=message.message_id,
            original_name=original_name,
            data=raw_bytes,
        )

        # Step 3: Extract text
        text = await asyncio.to_thread(extract_text, content_type, raw_bytes)

        # Step 4: AI analysis
        ai_result = await asyncio.to_thread(analyze_content, text, content_type)

        # Step 5: Store metadata in database
        db_item = await asyncio.to_thread(
            db.save_content_item,
            content_type=content_type,
            file_path=str(file_path),
            original_name=original_name,
            telegram_message_id=message.message_id,
            telegram_user_id=update.effective_user.id,
            tags=", ".join(ai_result["tags"]),
            summary=ai_result["summary"],
            topic=ai_result["topic"],
        )

        # Step 5.5: Make and persist decision
        decision = await _make_and_persist_decision(
            content_type=content_type,
            has_trigger=should_publish,
            ai_result=ai_result,
            item_id=db_item.id,
            telegram_message_id=message.message_id,
        )

        # Step 6: Publish to GitHub if decision recommends it
        if decision["recommendation"] == "publish_to_github":
            await _publish_to_github(
                content_type=content_type,
                original_name=original_name,
                text=text,
                raw_bytes=raw_bytes,
                ai_result=ai_result,
                item_id=db_item.id,
                message=message,
            )

        # Step 7: Respond
        await message.reply_text(
            f"Saved: {original_name}\n"
            f"Type: {content_type}\n"
            f"Topic: {ai_result['topic']}\n"
            f"Tags: {', '.join(ai_result['tags'])}\n"
            f"Summary: {ai_result['summary']}"
        )

    except Exception:
        logger.exception("Failed to process document for message_id=%s", message.message_id)
        await message.reply_text(
            "An error occurred while processing your document. "
            "Please check the logs for details."
        )


# ── Photo handler ───────────────────────────────────────────────────────────


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    message = update.effective_message
    if not message or not message.photo:
        return

    # Get the highest resolution photo
    photo = message.photo[-1]
    original_name = f"photo_{photo.file_unique_id}.jpg"
    content_type = "images"

    # Check for publish trigger in caption
    should_publish = _has_publish_trigger(message.caption)

    await message.reply_text("Received image. Processing...")

    try:
        # Step 1: Download
        tg_file = await photo.get_file()
        data = await tg_file.download_as_bytearray()
        raw_bytes = bytes(data)

        # Step 2: Save raw file
        file_path = await asyncio.to_thread(
            save_file,
            content_type=content_type,
            topic="general",
            telegram_message_id=message.message_id,
            original_name=original_name,
            data=raw_bytes,
        )

        # Step 3: Caption text for AI analysis
        caption_text = message.caption or ""
        if caption_text:
            ai_result = await asyncio.to_thread(analyze_content, caption_text, content_type)
        else:
            ai_result = {
                "tags": ["image"],
                "summary": "Image received without caption.",
                "topic": "general",
            }

        # Step 4: Store metadata
        db_item = await asyncio.to_thread(
            db.save_content_item,
            content_type=content_type,
            file_path=str(file_path),
            original_name=original_name,
            telegram_message_id=message.message_id,
            telegram_user_id=update.effective_user.id,
            tags=", ".join(ai_result["tags"]),
            summary=ai_result["summary"],
            topic=ai_result["topic"],
        )

        # Step 4.5: Make and persist decision
        decision = await _make_and_persist_decision(
            content_type=content_type,
            has_trigger=should_publish,
            ai_result=ai_result,
            item_id=db_item.id,
            telegram_message_id=message.message_id,
        )

        # Step 5: Publish to GitHub if decision recommends it
        if decision["recommendation"] == "publish_to_github":
            await _publish_to_github(
                content_type=content_type,
                original_name=original_name,
                text=caption_text,
                raw_bytes=raw_bytes,
                ai_result=ai_result,
                item_id=db_item.id,
                message=message,
            )

        await message.reply_text(
            "Saved image.\n"
            f"Topic: {ai_result['topic']}\n"
            f"Tags: {', '.join(ai_result['tags'])}\n"
            f"Summary: {ai_result['summary']}"
        )

    except Exception:
        logger.exception("Failed to process photo for message_id=%s", message.message_id)
        await message.reply_text(
            "An error occurred while processing your image. "
            "Please check the logs for details."
        )


# ── Text / Link handler ────────────────────────────────────────────────────


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not _is_authorized(update.effective_user.id):
        await _reject_unauthorized(update)
        return

    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    if not text:
        return

    # Detect if this is a URL
    urls = URL_PATTERN.findall(text)

    if urls:
        await _handle_link(update, message, text, urls[0])
    else:
        await _handle_note(update, message, text)


async def _handle_link(update, message, text, url):
    content_type = "links"
    original_name = url[:100]

    # Check for publish trigger
    should_publish = _has_publish_trigger(text)

    await message.reply_text("Received link. Processing...")

    try:
        # Step 1: Save the raw link text
        file_path = await asyncio.to_thread(
            save_text_content,
            content_type=content_type,
            topic="general",
            telegram_message_id=message.message_id,
            original_name=f"link_{message.message_id}.txt",
            text=text,
        )

        # Step 2: Extract text from URL
        extracted = await asyncio.to_thread(extract_text, "links", None, url)

        # Step 3: AI analysis
        if extracted:
            combined_text = f"URL: {url}\n\n{extracted}"
        else:
            combined_text = f"URL: {url}\n\n{text}"
        ai_result = await asyncio.to_thread(analyze_content, combined_text, content_type)

        # Step 4: Store metadata
        db_item = await asyncio.to_thread(
            db.save_content_item,
            content_type=content_type,
            file_path=str(file_path),
            original_name=original_name,
            telegram_message_id=message.message_id,
            telegram_user_id=update.effective_user.id,
            tags=", ".join(ai_result["tags"]),
            summary=ai_result["summary"],
            topic=ai_result["topic"],
        )

        # Step 4.5: Make and persist decision
        decision = await _make_and_persist_decision(
            content_type=content_type,
            has_trigger=should_publish,
            ai_result=ai_result,
            item_id=db_item.id,
            telegram_message_id=message.message_id,
        )

        # Step 5: Publish to GitHub if decision recommends it
        if decision["recommendation"] == "publish_to_github":
            await _publish_to_github(
                content_type=content_type,
                original_name=original_name,
                text=combined_text,
                raw_bytes=None,
                ai_result=ai_result,
                item_id=db_item.id,
                message=message,
            )

        await message.reply_text(
            f"Saved link.\n"
            f"Topic: {ai_result['topic']}\n"
            f"Tags: {', '.join(ai_result['tags'])}\n"
            f"Summary: {ai_result['summary']}"
        )

    except Exception:
        logger.exception("Failed to process link for message_id=%s", message.message_id)
        await message.reply_text(
            "An error occurred while processing your link. "
            "Please check the logs for details."
        )


async def _handle_note(update, message, text):
    content_type = "notes"
    original_name = f"note_{message.message_id}.txt"

    # Check for publish trigger
    should_publish = _has_publish_trigger(text)

    await message.reply_text("Received note. Processing...")

    try:
        # Step 1: Save raw text
        file_path = await asyncio.to_thread(
            save_text_content,
            content_type=content_type,
            topic="general",
            telegram_message_id=message.message_id,
            original_name=original_name,
            text=text,
        )

        # Step 2: AI analysis
        ai_result = await asyncio.to_thread(analyze_content, text, content_type)

        # Step 3: Store metadata
        db_item = await asyncio.to_thread(
            db.save_content_item,
            content_type=content_type,
            file_path=str(file_path),
            original_name=original_name,
            telegram_message_id=message.message_id,
            telegram_user_id=update.effective_user.id,
            tags=", ".join(ai_result["tags"]),
            summary=ai_result["summary"],
            topic=ai_result["topic"],
        )

        # Step 3.5: Make and persist decision
        decision = await _make_and_persist_decision(
            content_type=content_type,
            has_trigger=should_publish,
            ai_result=ai_result,
            item_id=db_item.id,
            telegram_message_id=message.message_id,
        )

        # Step 4: Publish to GitHub if decision recommends it
        if decision["recommendation"] == "publish_to_github":
            await _publish_to_github(
                content_type=content_type,
                original_name=original_name,
                text=text,
                raw_bytes=None,
                ai_result=ai_result,
                item_id=db_item.id,
                message=message,
            )

        await message.reply_text(
            f"Saved note.\n"
            f"Topic: {ai_result['topic']}\n"
            f"Tags: {', '.join(ai_result['tags'])}\n"
            f"Summary: {ai_result['summary']}"
        )

    except Exception:
        logger.exception("Failed to process note for message_id=%s", message.message_id)
        await message.reply_text(
            "An error occurred while processing your note. "
            "Please check the logs for details."
        )
