import time
from datetime import datetime
from pathlib import Path

from bots.tse_bot import TseBot
from config import TSE_URL
from services.excel_service import ExcelService
from services.file_service import FileService


class BotProcessor:
    """Orquesta la lectura, consulta y escritura sobre el mismo Excel."""

    def __init__(self, file_service: FileService, logger, bot_factory: type[TseBot] = TseBot) -> None:
        self.file_service = file_service
        self.logger = logger
        self.bot_factory = bot_factory

    def procesar(self) -> Path:
        ruta_archivo = self.file_service.obtener_archivo_excel()
        excel = ExcelService(ruta_archivo)
        bot = self.bot_factory(TSE_URL, self.logger)

        self.logger.info("Procesando archivo: %s", ruta_archivo.name)

        try:
            bot.abrir()
            self._procesar_filas(excel, bot)
            excel.guardar()
            self.logger.info("Archivo actualizado correctamente: %s", ruta_archivo.name)
            return ruta_archivo
        finally:
            bot.cerrar()

    def _procesar_filas(self, excel: ExcelService, bot: TseBot) -> None:
        total = excel.total_consultas()

        for indice, (fila, cedula) in enumerate(excel.iterar_cedulas(), start=1):
            nombre, estado = self._resolver_consulta(bot, cedula)
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            excel.escribir_resultado(fila, nombre, estado, fecha_hora)
            self._registrar_progreso(indice, total, cedula, estado)

            if indice % 10 == 0:
                excel.guardar()
                self.logger.info("Guardado parcial tras %s consultas", indice)

            self._esperar_entre_consultas(indice, total)

    @staticmethod
    def _resolver_consulta(bot: TseBot, cedula: str) -> tuple[str, str]:
        if not cedula:
            return "", "Cédula vacía"
        if not cedula.isdigit() or len(cedula) != 9:
            return "", "Cédula inválida"
        return bot.consultar_cedula(cedula)

    def _registrar_progreso(self, indice: int, total: int, cedula: str, estado: str) -> None:
        mensaje = f"Procesada {indice}/{total} | Cédula: {cedula or '[vacía]'} | Estado: {estado}"
        print(mensaje)
        self.logger.info(mensaje)

    @staticmethod
    def _esperar_entre_consultas(indice: int, total: int) -> None:
        if indice < total:
            time.sleep(1)
