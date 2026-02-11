import os


def test_required_env_vars_are_set():
    required = [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_USER_ID",
        "OPENAI_API_KEY",
        "STORAGE_BASE_PATH",
        "DATABASE_URL",
        "ENVIRONMENT",
    ]
    for var in required:
        assert os.getenv(var), f"Missing env var: {var}"


def test_allowed_user_id_is_integer():
    value = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "")
    assert value.isdigit(), "TELEGRAM_ALLOWED_USER_ID must be a numeric string"
