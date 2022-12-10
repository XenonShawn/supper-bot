from datetime import datetime
import logging
import os

from supperbot.bot import application

from config import LOGGING_LEVEL, LOCAL


def main():
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

    application.run_polling()


if __name__ == "__main__":
    main()
