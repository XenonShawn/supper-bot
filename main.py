"""Start the bot and set up logging."""
from datetime import datetime
import logging
import os

from supperbot.bot import application

from config import LOGGING_LEVEL, LOCAL, PORT, TOKEN, URL


def main():
    # Create a logs file if it does not exist
    if not os.path.exists("logs"):
        os.mkdir("logs")

    # Log to stdout and to file (if local deployment)
    logging.basicConfig(
        format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S %p",
        level=LOGGING_LEVEL,
        handlers=[logging.StreamHandler()]
        + [
            logging.FileHandler(os.path.join("logs", f"{datetime.today().date()}.log")),
        ]
        if LOCAL
        else [],
    )
    logging.info("Hello world, initializing bot!")

    if LOCAL:
        if os.name == "nt":
            # Required on Windows systems so that the bot won't throw warnings on init
            # For more information, read
            # https://docs.python-telegram-bot.org/en/latest/telegram.ext.application.html#telegram.ext.Application.run_polling.params.stop_signals
            application.run_polling(stop_signals=None)
        else:
            application.run_polling()
    else:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=URL + TOKEN,
        )


if __name__ == "__main__":
    main()
