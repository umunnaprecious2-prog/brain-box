import logging
import sys


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger(__name__)

    # Config is validated on import — will sys.exit(1) if env vars are missing
    from app.config.settings import ENVIRONMENT

    logger.info("Starting Brain Box (%s)...", ENVIRONMENT)

    # Initialize storage directories
    from app.storage.file_storage import init_storage

    init_storage()

    # Initialize database schema
    from app.database.repository import init_db

    init_db()

    # Create and run the Telegram bot
    from app.telegram.bot import create_bot_application

    bot_app = create_bot_application()
    logger.info("Brain Box is running. Press Ctrl+C to stop.")
    bot_app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
