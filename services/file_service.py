from pathlib import Path


class FileService:
    """Busca y valida el archivo Excel a procesar."""

    extensiones_permitidas = {".xlsx"}

    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir

    def obtener_archivo_excel(self) -> Path:
        archivos = sorted(
            archivo
            for archivo in self.upload_dir.iterdir()
            if archivo.is_file() and self.es_archivo_valido(archivo)
        )

        if not archivos:
            raise FileNotFoundError("No hay archivos .xlsx dentro de uploads/")
        if len(archivos) > 1:
            raise RuntimeError("Hay más de un archivo .xlsx en uploads/. Deja solo uno para procesar.")

        return archivos[0]

    def es_archivo_valido(self, ruta_archivo: Path) -> bool:
        return ruta_archivo.suffix.lower() in self.extensiones_permitidas
