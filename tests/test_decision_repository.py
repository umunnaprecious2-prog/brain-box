import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.models import Base, Decision
from app.database.repository import (
    get_decisions_by_content_item,
    get_recent_decisions,
    save_decision,
)


def test_save_decision():
    """Test saving a decision to the database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        # Mock the module-level engine
        import app.database.repository as repo

        original_engine = repo.engine
        repo.engine = engine

        try:
            decision = save_decision(
                decision_name="test_decision",
                context="Test context",
                options="Option 1\nOption 2",
                recommendation="publish_to_github",
                rationale="Test rationale",
                confidence="high",
                content_item_id=1,
                telegram_message_id=123,
            )

            assert decision.id is not None
            assert decision.decision_name == "test_decision"
            assert decision.recommendation == "publish_to_github"
            assert decision.confidence == "high"
            assert decision.content_item_id == 1
            assert decision.telegram_message_id == 123

        finally:
            repo.engine = original_engine
            engine.dispose()


def test_get_decisions_by_content_item():
    """Test retrieving decisions by content item ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            # Create test decisions
            d1 = Decision(
                decision_name="decision1",
                context="context1",
                options="opt1",
                recommendation="publish_to_github",
                rationale="rationale1",
                confidence="high",
                content_item_id=1,
            )
            d2 = Decision(
                decision_name="decision2",
                context="context2",
                options="opt2",
                recommendation="store_locally_only",
                rationale="rationale2",
                confidence="medium",
                content_item_id=1,
            )
            d3 = Decision(
                decision_name="decision3",
                context="context3",
                options="opt3",
                recommendation="publish_to_github",
                rationale="rationale3",
                confidence="high",
                content_item_id=2,
            )
            session.add_all([d1, d2, d3])
            session.commit()

        import app.database.repository as repo

        original_engine = repo.engine
        repo.engine = engine

        try:
            decisions = get_decisions_by_content_item(1)
            assert len(decisions) == 2
            assert all(d.content_item_id == 1 for d in decisions)

        finally:
            repo.engine = original_engine
            engine.dispose()


def test_get_recent_decisions():
    """Test retrieving recent decisions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            # Create multiple test decisions
            for i in range(5):
                decision = Decision(
                    decision_name=f"decision{i}",
                    context=f"context{i}",
                    options="opts",
                    recommendation="publish_to_github",
                    rationale="rationale",
                    confidence="high",
                )
                session.add(decision)
            session.commit()

        import app.database.repository as repo

        original_engine = repo.engine
        repo.engine = engine

        try:
            decisions = get_recent_decisions(limit=3)
            assert len(decisions) == 3

        finally:
            repo.engine = original_engine
            engine.dispose()


def test_decision_model_repr():
    """Test Decision model string representation."""
    decision = Decision(
        decision_name="test",
        context="ctx",
        options="opts",
        recommendation="publish_to_github",
        rationale="reason",
        confidence="high",
    )
    repr_str = repr(decision)
    assert "Decision" in repr_str
    assert "test" in repr_str
    assert "publish_to_github" in repr_str
