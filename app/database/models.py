import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    github_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    github_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<ContentItem(id={self.id}, "
            f"type={self.content_type}, "
            f"name={self.original_name})>"
        )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    content_item_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<Decision(id={self.id}, "
            f"name={self.decision_name}, "
            f"recommendation={self.recommendation})>"
        )
