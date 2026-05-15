import re
from typing import Optional

from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class TseBot:
    """Controls Chrome and queries IDs on the TSE website."""

    method = "selenium"

    def __init__(self, url: str, logger) -> None:
        self.url = url
        self.logger = logger
        self.driver: Optional[webdriver.Chrome] = None

    def open(self) -> None:
        options = ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def close(self) -> None:
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
            self.logger.info("Chrome cerrado correctamente")

    def query_id(self, id_number: str) -> tuple[str, str]:
        if self.driver is None:
            raise RuntimeError("El navegador no está abierto")

        try:
            self._navigate_to_query()
            initial_text = self._get_page_text()
            self._enter_id(id_number)
            return self._read_result(initial_text)
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Fallo consultando cédula %s", id_number)
            return "", f"Error: {exc}"

    def _navigate_to_query(self) -> None:
        assert self.driver is not None
        self.driver.get(self.url)

    def _enter_id(self, id_number: str) -> None:
        assert self.driver is not None
        wait = WebDriverWait(self.driver, 15)
        field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
        field.clear()
        field.send_keys(id_number)
        field.send_keys(Keys.ENTER)

    def _read_result(self, initial_text: str) -> tuple[str, str]:
        assert self.driver is not None
        wait = WebDriverWait(self.driver, 10)
        wait.until(lambda driver: self._get_page_text() != initial_text)
        body_text = self._get_page_text().lower()

        if "error de conexión" in body_text:
            raise RuntimeError("El sitio del TSE mostró error de conexión")
        if "no se encontró" in body_text or "no existe" in body_text:
            return "", "No encontrado"

        name = self._extract_name()
        if name:
            return name, "Consultado"
        return "", "Sin nombre detectado"

    def _get_page_text(self) -> str:
        assert self.driver is not None
        return self.driver.find_element(By.TAG_NAME, "body").text

    def _extract_name(self) -> Optional[str]:
        assert self.driver is not None
        selectors = [
            (By.ID, "lblNombre"),
            (By.ID, "lblNombreCompleto"),
            (By.XPATH, "//*[contains(translate(text(),'NOMBRE','nombre'),'nombre')]/following::td[1]"),
            (By.XPATH, "//*[contains(translate(text(),'NOMBRE','nombre'),'nombre')]/following::*[1]"),
        ]

        for by, selector in selectors:
            for element in self.driver.find_elements(by, selector):
                text = element.text.strip()
                if text and "nombre" not in text.lower():
                    return text

        return self._extract_name_from_text()

    def _extract_name_from_text(self) -> Optional[str]:
        assert self.driver is not None
        ignored_lines = (
            "favor digitar",
            "debe utilizar",
            "tribunal supremo",
            "derechos reservados",
            "error de conexión",
            "inicio consultar",
            "consultar cédula",
            "consultar nombre",
        )

        for line in self.driver.find_element(By.TAG_NAME, "body").text.splitlines():
            text = line.strip()
            if not text:
                continue
            if any(noise in text.lower() for noise in ignored_lines):
                continue
            if len(text.split()) >= 2 and not re.fullmatch(r"\d+", text):
                return text
        return None
