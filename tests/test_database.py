from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.models import Base, ContentItem


def test_content_item_model(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = ContentItem(
            content_type="notes",
            file_path="/tmp/test.txt",
            original_name="test.txt",
            telegram_message_id=123,
            telegram_user_id=456,
            tags="test, demo",
            summary="A test note.",
            topic="general",
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        assert item.id is not None
        assert item.content_type == "notes"
        assert item.original_name == "test.txt"
        assert item.tags == "test, demo"


def test_content_item_repr(tmp_path):
    item = ContentItem(
        id=1,
        content_type="documents",
        file_path="/tmp/doc.pdf",
        original_name="doc.pdf",
        telegram_message_id=1,
        telegram_user_id=1,
    )
    assert "ContentItem" in repr(item)
    assert "documents" in repr(item)


def test_query_by_content_type(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        for i in range(3):
            session.add(
                ContentItem(
                    content_type="images",
                    file_path=f"/tmp/img{i}.jpg",
                    original_name=f"img{i}.jpg",
                    telegram_message_id=i,
                    telegram_user_id=1,
                )
            )
        session.add(
            ContentItem(
                content_type="notes",
                file_path="/tmp/note.txt",
                original_name="note.txt",
                telegram_message_id=99,
                telegram_user_id=1,
            )
        )
        session.commit()

    from sqlalchemy import select

    with Session(engine) as session:
        stmt = select(ContentItem).where(ContentItem.content_type == "images")
        results = list(session.scalars(stmt).all())
        assert len(results) == 3
