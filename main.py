from config import UPLOAD_DIR, create_base_dirs
from logger_config import configure_logging
from processors.bot_processor import BotProcessor
from services.file_service import FileService


def main() -> None:
    create_base_dirs()
    logger = configure_logging()
    processor = BotProcessor(FileService(UPLOAD_DIR), logger)

    try:
        updated_file = processor.process()
        print(f"Proceso finalizado. Archivo actualizado: {updated_file.name}")
    except FileNotFoundError as exc:
        logger.warning(str(exc))
        print("No hay archivos Excel en uploads/. Coloca un .xlsx y vuelve a ejecutar.")


if __name__ == "__main__":
    main()
