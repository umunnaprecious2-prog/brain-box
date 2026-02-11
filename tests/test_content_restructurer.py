from unittest.mock import patch

from app.agents.content_restructurer import (
    _build_default_markdown,
    _fallback_result,
    _validate_result,
    restructure_for_github,
)


def test_fallback_result_structure():
    """Test fallback produces all required keys."""
    result = _fallback_result(
        content_type="notes",
        original_name="test_note.txt",
        tags=["test", "demo"],
        summary="A test note.",
        topic="general",
    )

    assert "markdown" in result
    assert "suggested_subfolder" in result
    assert "suggested_filename" in result
    assert "commit_message" in result
    assert result["suggested_subfolder"] == "general"
    assert result["suggested_filename"].endswith(".md")
    assert "notes" in result["commit_message"]


def test_fallback_result_sanitizes_filename():
    """Test fallback handles special characters in filenames."""
    result = _fallback_result(
        content_type="documents",
        original_name="My Document (Final).pdf",
        tags=["doc"],
        summary="Summary",
        topic="work",
    )

    assert " " not in result["suggested_filename"]
    assert "(" not in result["suggested_filename"]
    assert result["suggested_filename"].endswith(".md")


def test_build_default_markdown():
    """Test default markdown generation."""
    md = _build_default_markdown(
        original_name="test.txt",
        tags=["python", "code"],
        summary="A code snippet.",
    )

    assert "# test.txt" in md
    assert "A code snippet." in md
    assert "`python`" in md
    assert "`code`" in md


def test_validate_result_sanitizes_subfolder():
    """Test validation sanitizes subfolder names."""
    result = _validate_result(
        result={
            "markdown": "# Test",
            "suggested_subfolder": "My Folder!@#",
            "suggested_filename": "test.md",
            "commit_message": "Add test",
        },
        content_type="notes",
        original_name="test.txt",
        tags=["test"],
        summary="Summary",
    )

    # Special characters should be replaced with hyphens
    assert all(c.isalnum() or c == "-" for c in result["suggested_subfolder"])


def test_validate_result_ensures_md_extension():
    """Test validation ensures .md extension on filename."""
    result = _validate_result(
        result={
            "markdown": "# Test",
            "suggested_subfolder": "general",
            "suggested_filename": "test.txt",
            "commit_message": "Add test",
        },
        content_type="notes",
        original_name="test.txt",
        tags=["test"],
        summary="Summary",
    )

    assert result["suggested_filename"].endswith(".md")


def test_validate_result_truncates_commit_message():
    """Test validation truncates long commit messages."""
    long_msg = "A" * 200
    result = _validate_result(
        result={
            "markdown": "# Test",
            "suggested_subfolder": "general",
            "suggested_filename": "test.md",
            "commit_message": long_msg,
        },
        content_type="notes",
        original_name="test.txt",
        tags=["test"],
        summary="Summary",
    )

    assert len(result["commit_message"]) <= 120


@patch("app.agents.content_restructurer._client")
def test_restructure_for_github_empty_text(mock_client):
    """Test restructure falls back gracefully for empty text."""
    result = restructure_for_github(
        text="",
        content_type="notes",
        original_name="empty.txt",
        tags=["empty"],
        summary="Empty content.",
        topic="general",
    )

    assert result["suggested_subfolder"] == "general"
    mock_client.chat.completions.create.assert_not_called()


@patch("app.agents.content_restructurer._client")
def test_restructure_for_github_api_failure(mock_client):
    """Test restructure falls back gracefully on API failure."""
    mock_client.chat.completions.create.side_effect = Exception("API error")

    result = restructure_for_github(
        text="Some content to restructure.",
        content_type="notes",
        original_name="test.txt",
        tags=["test"],
        summary="A test.",
        topic="technology",
    )

    assert "markdown" in result
    assert result["suggested_subfolder"] == "technology"
