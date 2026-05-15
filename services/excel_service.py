import re
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook
from openpyxl.styles import PatternFill


class ExcelService:
    """Reads and updates the input Excel file in place."""

    soft_red_fill = PatternFill(fill_type="solid", fgColor="FCE4D6")
    soft_yellow_fill = PatternFill(fill_type="solid", fgColor="FFF2CC")

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.workbook = load_workbook(file_path)
        self.sheet = self.workbook.active
        self.start_row = self._detect_start_row()
        self._create_headers_if_needed()

    def _detect_start_row(self) -> int:
        first_id = self.clean_id(self.sheet.cell(row=1, column=1).value)
        return 2 if not first_id.isdigit() else 1

    def _create_headers_if_needed(self) -> None:
        if self.start_row != 2:
            return

        headers = {
            2: "Nombre completo",
            3: "Estado",
            4: "Fecha y hora de consulta",
            5: "Método de consulta",
        }
        for column, title in headers.items():
            if self.sheet.cell(row=1, column=column).value is None:
                self.sheet.cell(row=1, column=column).value = title

    @staticmethod
    def clean_id(value: object) -> str:
        if value is None:
            return ""
        return re.sub(r"[\s-]+", "", str(value).strip())

    def iter_ids(self) -> Iterable[tuple[int, str]]:
        for row in range(self.start_row, self.sheet.max_row + 1):
            id_number = self.clean_id(self.sheet.cell(row=row, column=1).value)
            yield row, id_number

    def total_queries(self) -> int:
        return max(self.sheet.max_row - self.start_row + 1, 0)

    def write_result(self, row: int, name: str, status: str, queried_at: str, method: str) -> None:
        self.sheet.cell(row=row, column=2).value = name
        self.sheet.cell(row=row, column=3).value = status
        self.sheet.cell(row=row, column=4).value = queried_at
        self.sheet.cell(row=row, column=5).value = method
        self._apply_row_fill(row, status)

    def save(self) -> None:
        self.workbook.save(self.file_path)

    def _apply_row_fill(self, row: int, status: str) -> None:
        fill = None
        if status == "Cédula inválida":
            fill = self.soft_red_fill
        elif status == "No encontrado":
            fill = self.soft_yellow_fill

        if fill is None:
            return

        for column in range(1, self.sheet.max_column + 1):
            self.sheet.cell(row=row, column=column).fill = fill
