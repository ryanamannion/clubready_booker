import logging.handlers
import os

__version__ = "0.0.2-dev"

LOGFILE = "clubready_booker.log"
LOGLEVEL = os.environ.get("LOGLEVEL", logging.INFO)

file_handler = logging.handlers.RotatingFileHandler(
    LOGFILE, maxBytes=2000000, backupCount=3
)


handlers = [file_handler, logging.StreamHandler()]

msg_format = (
    "%(asctime)s: [%(filename)s:%(lineno)s - %(funcName)s ] "
    "%(levelname)s  %(message)s"
)

logging.basicConfig(
    level=LOGLEVEL,
    format=msg_format,
    handlers=handlers
)

logging.info(f"Running clubready_booker on version {__version__}")
