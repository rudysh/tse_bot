import time
from datetime import datetime
from pathlib import Path
from typing import Protocol

from bots.bot_factory import create_bot
from config import TSE_URL
from services.excel_service import ExcelService
from services.file_service import FileService


class BotLike(Protocol):
    method: str

    def open(self) -> None: ...

    def close(self) -> None: ...

    def query_id(self, id_number: str) -> tuple[str, str]: ...


class BotProcessor:
    """Coordinates reading, querying, and writing within the same Excel file."""

    def __init__(self, file_service: FileService, logger, bot_factory=create_bot) -> None:
        self.file_service = file_service
        self.logger = logger
        self.bot_factory = bot_factory

    def process(self) -> Path:
        file_path = self.file_service.get_excel_file()
        excel = ExcelService(file_path)
        bot = self.bot_factory(TSE_URL, self.logger)

        self.logger.info("Procesando archivo: %s", file_path.name)

        try:
            bot.open()
            self._process_rows(excel, bot)
            excel.save()
            self.logger.info("Archivo actualizado correctamente: %s", file_path.name)
            return file_path
        finally:
            bot.close()

    def _process_rows(self, excel: ExcelService, bot: BotLike) -> None:
        total = excel.total_queries()

        for index, (row, id_number) in enumerate(excel.iter_ids(), start=1):
            name, status = self._resolve_query(bot, id_number)
            queried_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            excel.write_result(row, name, status, queried_at, bot.method)
            self._log_progress(index, total, id_number, status)

            if index % 10 == 0:
                excel.save()
                self.logger.info("Guardado parcial tras %s consultas", index)

            self._wait_between_queries(index, total)

    @staticmethod
    def _resolve_query(bot: BotLike, id_number: str) -> tuple[str, str]:
        if not id_number:
            return "", "Cédula vacía"
        if not id_number.isdigit() or len(id_number) != 9:
            return "", "Cédula inválida"
        return bot.query_id(id_number)

    def _log_progress(self, index: int, total: int, id_number: str, status: str) -> None:
        message = f"Procesada {index}/{total} | Cédula: {id_number or '[vacía]'} | Estado: {status}"
        print(message)
        self.logger.info(message)

    @staticmethod
    def _wait_between_queries(index: int, total: int) -> None:
        if index < total:
            time.sleep(1)
