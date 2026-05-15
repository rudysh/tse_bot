from bots.tse_bot import TseBot
from bots.tse_request_bot import TseRequestBot
from config import BOT_MODE


def create_bot(url: str, logger):
    mode = BOT_MODE.lower().strip()
    if mode == "api_request":
        return TseRequestBot(url, logger)
    if mode != "selenium":
        logger.warning("BOT_MODE inválido '%s'. Se usará selenium por defecto.", BOT_MODE)
    return TseBot(url, logger)
