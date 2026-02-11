import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.config.settings import PROXY_URL, TELEGRAM_BOT_TOKEN
from app.telegram.handlers import (
    date_handler,
    document_handler,
    help_handler,
    list_handler,
    photo_handler,
    publish_handler,
    search_handler,
    start_handler,
    text_handler,
)

logger = logging.getLogger(__name__)


def create_bot_application():
    builder = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(10.0)
    )

    if PROXY_URL:
        logger.info("Using proxy for Telegram: %s", PROXY_URL)
        builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)

    app = builder.build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("list", list_handler))
    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(CommandHandler("date", date_handler))
    app.add_handler(CommandHandler("publish", publish_handler))

    # Content handlers
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Telegram bot handlers registered.")
    return app
