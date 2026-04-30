import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import config
from handlers.command_handler import (
    cmd_start, cmd_help, cmd_input, cmd_laporan,
    cmd_budget, cmd_history, cmd_edit, cmd_hapus,
    cmd_export, cmd_setcurrency,
)
from handlers.input_handler import handle_message
from handlers.callback_handler import handle_callback

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_app() -> Application:
    app = Application.builder().token(config.telegram_bot_token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("input", cmd_input))
    app.add_handler(CommandHandler("laporan", cmd_laporan))
    app.add_handler(CommandHandler("budget", cmd_budget))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("edit", cmd_edit))
    app.add_handler(CommandHandler("hapus", cmd_hapus))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("setcurrency", cmd_setcurrency))

    # Inline keyboard callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    # All non-command messages: text, photo, document, voice, audio
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND
        | filters.PHOTO
        | filters.Document.MimeType("application/pdf")
        | filters.VOICE
        | filters.AUDIO,
        handle_message,
    ))

    return app


if __name__ == "__main__":
    logger.info("Starting agen_exptrackerviz...")
    app = build_app()
    app.run_polling(drop_pending_updates=True)
