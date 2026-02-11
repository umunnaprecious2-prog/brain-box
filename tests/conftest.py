import os

import pytest

# Set test environment variables BEFORE any app imports
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-123")
os.environ.setdefault("TELEGRAM_ALLOWED_USER_ID", "12345")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("GITHUB_TOKEN", "test-github-token")
os.environ.setdefault("GITHUB_DEFAULT_REPO", "test-owner/test-repo")


@pytest.fixture
def tmp_storage(tmp_path):
    os.environ["STORAGE_BASE_PATH"] = str(tmp_path / "storage")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
    return tmp_path / "storage"
