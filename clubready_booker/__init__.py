import logging

__version__ = "0.0.0-dev"

logging.basicConfig(
    filename='clubready_booker.log',
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(message)s"
)

logging.info(f"Running clubready_booker on version {__version__}")
