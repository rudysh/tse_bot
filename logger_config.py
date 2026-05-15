import logging

from config import LOG_DIR


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "bot_tse.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("tse_bot")
