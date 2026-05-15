from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
LOG_DIR = BASE_DIR / "logs"
TSE_URL = "https://servicioselectorales.tse.go.cr/chc/consulta_cedula.aspx"


def crear_carpetas_base() -> None:
    for folder in (UPLOAD_DIR, LOG_DIR):
        folder.mkdir(parents=True, exist_ok=True)
