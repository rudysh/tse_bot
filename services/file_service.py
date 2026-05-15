from pathlib import Path


class FileService:
    """Finds and validates the Excel file to process."""

    allowed_extensions = {".xlsx"}

    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir

    def get_excel_file(self) -> Path:
        files = sorted(
            file
            for file in self.upload_dir.iterdir()
            if file.is_file() and self.is_valid_file(file)
        )

        if not files:
            raise FileNotFoundError("No hay archivos .xlsx dentro de uploads/")
        if len(files) > 1:
            raise RuntimeError("Hay más de un archivo .xlsx en uploads/. Deja solo uno para procesar.")

        return files[0]

    def is_valid_file(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.allowed_extensions
