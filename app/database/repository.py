import datetime
import logging
from collections.abc import Sequence

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import DATABASE_URL
from app.database.models import Base, ContentItem, Decision

logger = logging.getLogger(__name__)

# For SQLite, strip the sqlite:/// prefix for the engine path
_engine_url = DATABASE_URL
if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    # Relative path — resolve from project root
    from app.config.settings import STORAGE_BASE_PATH

    db_file = DATABASE_URL.replace("sqlite:///", "")
    STORAGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
    _engine_url = f"sqlite:///{STORAGE_BASE_PATH.parent / db_file}"

engine = create_engine(_engine_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    Base.metadata.create_all(engine)
    logger.info("Database schema initialized.")


def save_content_item(
    content_type: str,
    file_path: str,
    original_name: str,
    telegram_message_id: int,
    telegram_user_id: int,
    tags: str | None = None,
    summary: str | None = None,
    topic: str | None = None,
) -> ContentItem:
    with Session(engine) as session:
        item = ContentItem(
            content_type=content_type,
            file_path=file_path,
            original_name=original_name,
            telegram_message_id=telegram_message_id,
            telegram_user_id=telegram_user_id,
            tags=tags,
            summary=summary,
            topic=topic,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        logger.info("Saved content item id=%s type=%s", item.id, content_type)
        return item


def update_content_ai_fields(
    item_id: int,
    tags: str | None = None,
    summary: str | None = None,
    topic: str | None = None,
) -> None:
    with Session(engine) as session:
        item = session.get(ContentItem, item_id)
        if item is None:
            logger.warning("Content item %s not found for AI update.", item_id)
            return
        if tags is not None:
            item.tags = tags
        if summary is not None:
            item.summary = summary
        if topic is not None:
            item.topic = topic
        session.commit()
        logger.info("Updated AI fields for content item id=%s", item_id)


def list_by_content_type(content_type: str) -> Sequence[ContentItem]:
    with Session(engine) as session:
        stmt = (
            select(ContentItem)
            .where(ContentItem.content_type == content_type)
            .order_by(ContentItem.created_at.desc())
        )
        return list(session.scalars(stmt).all())


def search_by_keyword(keyword: str) -> Sequence[ContentItem]:
    with Session(engine) as session:
        pattern = f"%{keyword}%"
        stmt = (
            select(ContentItem)
            .where(
                (ContentItem.original_name.ilike(pattern))
                | (ContentItem.tags.ilike(pattern))
                | (ContentItem.summary.ilike(pattern))
                | (ContentItem.topic.ilike(pattern))
            )
            .order_by(ContentItem.created_at.desc())
        )
        return list(session.scalars(stmt).all())


def filter_by_date(
    start: datetime.date, end: datetime.date | None = None
) -> Sequence[ContentItem]:
    with Session(engine) as session:
        start_dt = datetime.datetime.combine(start, datetime.time.min)
        end_dt = datetime.datetime.combine(end or start, datetime.time.max)
        stmt = (
            select(ContentItem)
            .where(ContentItem.created_at.between(start_dt, end_dt))
            .order_by(ContentItem.created_at.desc())
        )
        return list(session.scalars(stmt).all())


def update_github_status(
    item_id: int,
    github_url: str,
) -> None:
    with Session(engine) as session:
        item = session.get(ContentItem, item_id)
        if item is None:
            logger.warning("Content item %s not found for GitHub update.", item_id)
            return
        item.github_published = True
        item.github_url = github_url
        session.commit()
        logger.info("Updated GitHub status for content item id=%s", item_id)


def get_content_item_by_id(item_id: int) -> ContentItem | None:
    with Session(engine) as session:
        item = session.get(ContentItem, item_id)
        if item:
            session.expunge(item)
        return item


def get_latest_unpublished() -> Sequence[ContentItem]:
    with Session(engine) as session:
        stmt = (
            select(ContentItem)
            .where(ContentItem.github_published == False)  # noqa: E712
            .order_by(ContentItem.created_at.desc())
            .limit(20)
        )
        return list(session.scalars(stmt).all())


def save_decision(
    decision_name: str,
    context: str,
    options: str,
    recommendation: str,
    rationale: str,
    confidence: str,
    content_item_id: int | None = None,
    telegram_message_id: int | None = None,
) -> Decision:
    """Save a Decision Object to the database."""
    with Session(engine) as session:
        decision = Decision(
            decision_name=decision_name,
            context=context,
            options=options,
            recommendation=recommendation,
            rationale=rationale,
            confidence=confidence,
            content_item_id=content_item_id,
            telegram_message_id=telegram_message_id,
        )
        session.add(decision)
        session.commit()
        session.refresh(decision)
        logger.info(
            "Saved decision id=%s name=%s recommendation=%s",
            decision.id,
            decision_name,
            recommendation,
        )
        return decision


def get_decisions_by_content_item(content_item_id: int) -> Sequence[Decision]:
    """Get all decisions related to a specific content item."""
    with Session(engine) as session:
        stmt = (
            select(Decision)
            .where(Decision.content_item_id == content_item_id)
            .order_by(Decision.created_at.desc())
        )
        return list(session.scalars(stmt).all())


def get_recent_decisions(limit: int = 20) -> Sequence[Decision]:
    """Get the most recent decisions."""
    with Session(engine) as session:
        stmt = select(Decision).order_by(Decision.created_at.desc()).limit(limit)
        return list(session.scalars(stmt).all())
