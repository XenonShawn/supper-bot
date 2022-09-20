import logging
import os

LOCAL = False
LOGGING_LEVEL = logging.INFO

if not LOCAL:
    PORT = int(os.environ.get("PORT", "8443"))
    URL = os.environ.get("URL")
    TOKEN = os.environ.get("TOKEN")
    DATABASE = os.environ.get("DATABASE")
else:
    from secrets import TOKEN, DATABASE

    URL = None
    PORT = None
