import base64
import logging
from pathlib import PurePosixPath

from github import Auth, Github, GithubException

from app.config.settings import (
    GITHUB_CONTENT_TYPES,
    GITHUB_DEFAULT_REPO,
    GITHUB_TOKEN,
)

logger = logging.getLogger(__name__)

_auth = Auth.Token(GITHUB_TOKEN)
_github = Github(auth=_auth)


def _get_repo():
    return _github.get_repo(GITHUB_DEFAULT_REPO)


def ensure_repo_folders() -> None:
    """Create top-level content-type folders in the repo if they don't exist."""
    repo = _get_repo()
    for folder in GITHUB_CONTENT_TYPES:
        try:
            repo.get_contents(folder)
        except GithubException as exc:
            if exc.status == 404:
                repo.create_file(
                    path=f"{folder}/.gitkeep",
                    message=f"Initialize {folder}/ folder",
                    content="",
                )
                logger.info("Created GitHub folder: %s/", folder)
            else:
                raise


def publish_text_content(
    folder_path: str,
    filename: str,
    content: str,
    commit_message: str,
) -> str:
    """Publish text/markdown content to GitHub. Returns the file URL."""
    repo = _get_repo()
    file_path = str(PurePosixPath(folder_path) / filename)

    try:
        existing = repo.get_contents(file_path)
        result = repo.update_file(
            path=file_path,
            message=commit_message,
            content=content,
            sha=existing.sha,
        )
        logger.info("Updated file in GitHub: %s", file_path)
    except GithubException as exc:
        if exc.status == 404:
            _ensure_parent_folders(repo, folder_path)
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
            )
            logger.info("Created file in GitHub: %s", file_path)
        else:
            raise

    return result["content"].html_url


def publish_binary_content(
    folder_path: str,
    filename: str,
    data: bytes,
    commit_message: str,
) -> str:
    """Publish binary content (images, PDFs, etc.) to GitHub. Returns the file URL."""
    repo = _get_repo()
    file_path = str(PurePosixPath(folder_path) / filename)
    encoded = base64.b64encode(data).decode("ascii")

    try:
        existing = repo.get_contents(file_path)
        result = repo.update_file(
            path=file_path,
            message=commit_message,
            content=encoded,
            sha=existing.sha,
        )
        logger.info("Updated binary file in GitHub: %s", file_path)
    except GithubException as exc:
        if exc.status == 404:
            _ensure_parent_folders(repo, folder_path)
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=encoded,
            )
            logger.info("Created binary file in GitHub: %s", file_path)
        else:
            raise

    return result["content"].html_url


def _ensure_parent_folders(repo, folder_path: str) -> None:
    """Ensure all parent folders exist by checking for .gitkeep files."""
    parts = PurePosixPath(folder_path).parts
    for i in range(1, len(parts) + 1):
        partial = "/".join(parts[:i])
        try:
            repo.get_contents(partial)
        except GithubException as exc:
            if exc.status == 404:
                repo.create_file(
                    path=f"{partial}/.gitkeep",
                    message=f"Create folder {partial}/",
                    content="",
                )
                logger.info("Created GitHub folder: %s/", partial)
            else:
                raise


# Map local content types to GitHub repo folder names
CONTENT_TYPE_TO_GITHUB_FOLDER = {
    "images": "pictures",
    "documents": "documents",
    "links": "links",
    "notes": "notes",
}
