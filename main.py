from config import UPLOAD_DIR, crear_carpetas_base
from logger_config import configurar_logging
from processors.bot_processor import BotProcessor
from services.file_service import FileService


def main() -> None:
    crear_carpetas_base()
    logger = configurar_logging()
    processor = BotProcessor(FileService(UPLOAD_DIR), logger)

    try:
        archivo_actualizado = processor.procesar()
        print(f"Proceso finalizado. Archivo actualizado: {archivo_actualizado.name}")
    except FileNotFoundError as exc:
        logger.warning(str(exc))
        print("No hay archivos Excel en uploads/. Coloca un .xlsx y vuelve a ejecutar.")


if __name__ == "__main__":
    main()
