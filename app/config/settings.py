import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env", override=True)

REQUIRED_ENV_VARS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USER_ID",
    "OPENAI_API_KEY",
    "STORAGE_BASE_PATH",
    "DATABASE_URL",
    "ENVIRONMENT",
    "GITHUB_TOKEN",
    "GITHUB_DEFAULT_REPO",
]


def _validate_env() -> None:
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        print(
            f"FATAL: Missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)


_validate_env()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_ALLOWED_USER_ID: int = int(os.environ["TELEGRAM_ALLOWED_USER_ID"])
OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
STORAGE_BASE_PATH: Path = Path(os.environ["STORAGE_BASE_PATH"]).resolve()
DATABASE_URL: str = os.environ["DATABASE_URL"]
ENVIRONMENT: str = os.environ["ENVIRONMENT"]

CONTENT_TYPES = ["images", "documents", "links", "notes"]

GITHUB_TOKEN: str = os.environ["GITHUB_TOKEN"]
GITHUB_DEFAULT_REPO: str = os.environ["GITHUB_DEFAULT_REPO"]

GITHUB_CONTENT_TYPES = ["pictures", "documents", "audios", "links", "notes"]

# Optional proxy — not required, but used when set
PROXY_URL: str | None = os.getenv("PROXY_URL") or None
