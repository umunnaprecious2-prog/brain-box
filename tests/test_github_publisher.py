from unittest.mock import MagicMock, patch

from app.agents.github_publisher import CONTENT_TYPE_TO_GITHUB_FOLDER


def test_content_type_mapping():
    """Verify local content types map to correct GitHub folder names."""
    assert CONTENT_TYPE_TO_GITHUB_FOLDER["images"] == "pictures"
    assert CONTENT_TYPE_TO_GITHUB_FOLDER["documents"] == "documents"
    assert CONTENT_TYPE_TO_GITHUB_FOLDER["links"] == "links"
    assert CONTENT_TYPE_TO_GITHUB_FOLDER["notes"] == "notes"


def test_content_type_mapping_completeness():
    """Ensure all expected content types are mapped."""
    expected = {"images", "documents", "links", "notes"}
    assert set(CONTENT_TYPE_TO_GITHUB_FOLDER.keys()) == expected


@patch("app.agents.github_publisher._get_repo")
def test_ensure_repo_folders_creates_missing(mock_get_repo):
    """Test that ensure_repo_folders creates .gitkeep for missing folders."""
    from github import GithubException

    from app.agents.github_publisher import ensure_repo_folders

    mock_repo = MagicMock()

    # Simulate all folders missing (404)
    mock_repo.get_contents.side_effect = GithubException(
        status=404, data={"message": "Not Found"}, headers={}
    )
    mock_repo.create_file.return_value = None
    mock_get_repo.return_value = mock_repo

    ensure_repo_folders()

    # Should attempt to create .gitkeep for each missing folder
    assert (
        mock_repo.create_file.call_count == 5
    )  # pictures, documents, audios, links, notes


@patch("app.agents.github_publisher._get_repo")
def test_ensure_repo_folders_skips_existing(mock_get_repo):
    """Test that ensure_repo_folders skips existing folders."""
    mock_repo = MagicMock()

    # Simulate all folders exist
    mock_repo.get_contents.return_value = MagicMock()
    mock_get_repo.return_value = mock_repo

    from app.agents.github_publisher import ensure_repo_folders

    ensure_repo_folders()

    # Should not create any files
    mock_repo.create_file.assert_not_called()


@patch("app.agents.github_publisher._get_repo")
def test_publish_text_content_creates_new_file(mock_get_repo):
    """Test publishing a new text file to GitHub."""
    from github import GithubException

    from app.agents.github_publisher import publish_text_content

    mock_repo = MagicMock()

    # File doesn't exist yet
    mock_repo.get_contents.side_effect = GithubException(
        status=404, data={"message": "Not Found"}, headers={}
    )

    mock_content = MagicMock()
    mock_content.html_url = "https://github.com/user/repo/blob/main/notes/test.md"
    mock_repo.create_file.return_value = {"content": mock_content}
    mock_get_repo.return_value = mock_repo

    url = publish_text_content(
        folder_path="notes/general",
        filename="test.md",
        content="# Test\nHello world",
        commit_message="Add test note",
    )

    assert url == "https://github.com/user/repo/blob/main/notes/test.md"
    mock_repo.create_file.assert_called()


@patch("app.agents.github_publisher._get_repo")
def test_publish_text_content_updates_existing(mock_get_repo):
    """Test updating an existing file in GitHub."""
    from app.agents.github_publisher import publish_text_content

    mock_repo = MagicMock()

    # File already exists
    mock_existing = MagicMock()
    mock_existing.sha = "abc123"
    mock_repo.get_contents.return_value = mock_existing

    mock_content = MagicMock()
    mock_content.html_url = "https://github.com/user/repo/blob/main/notes/test.md"
    mock_repo.update_file.return_value = {"content": mock_content}
    mock_get_repo.return_value = mock_repo

    url = publish_text_content(
        folder_path="notes/general",
        filename="test.md",
        content="# Updated\nNew content",
        commit_message="Update test note",
    )

    assert url == "https://github.com/user/repo/blob/main/notes/test.md"
    mock_repo.update_file.assert_called_once()
