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
    """Controla Chrome y consulta cédulas en el TSE."""

    def __init__(self, url: str, logger) -> None:
        self.url = url
        self.logger = logger
        self.driver: Optional[webdriver.Chrome] = None

    def abrir(self) -> None:
        opciones = ChromeOptions()
        opciones.add_argument("--start-maximized")
        opciones.add_argument("--disable-notifications")
        opciones.add_argument("--disable-popup-blocking")
        servicio = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=servicio, options=opciones)

    def cerrar(self) -> None:
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
            self.logger.info("Chrome cerrado correctamente")

    def consultar_cedula(self, cedula: str) -> tuple[str, str]:
        if self.driver is None:
            raise RuntimeError("El navegador no está abierto")

        try:
            self._navegar_a_consulta()
            texto_inicial = self._obtener_texto_pagina()
            self._ingresar_cedula(cedula)
            return self._leer_resultado(texto_inicial)
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Fallo consultando cédula %s", cedula)
            return "", f"Error: {exc}"

    def _navegar_a_consulta(self) -> None:
        assert self.driver is not None
        self.driver.get(self.url)

    def _ingresar_cedula(self, cedula: str) -> None:
        assert self.driver is not None
        wait = WebDriverWait(self.driver, 15)
        campo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
        campo.clear()
        campo.send_keys(cedula)
        campo.send_keys(Keys.ENTER)

    def _leer_resultado(self, texto_inicial: str) -> tuple[str, str]:
        assert self.driver is not None
        wait = WebDriverWait(self.driver, 10)
        wait.until(lambda driver: self._obtener_texto_pagina() != texto_inicial)
        body_text = self._obtener_texto_pagina().lower()

        if "error de conexión" in body_text:
            raise RuntimeError("El sitio del TSE mostró error de conexión")
        if "no se encontró" in body_text or "no existe" in body_text:
            return "", "No encontrado"

        nombre = self._extraer_nombre()
        if nombre:
            return nombre, "Consultado"
        return "", "Sin nombre detectado"

    def _obtener_texto_pagina(self) -> str:
        assert self.driver is not None
        return self.driver.find_element(By.TAG_NAME, "body").text

    def _extraer_nombre(self) -> Optional[str]:
        assert self.driver is not None
        selectores = [
            (By.ID, "lblNombre"),
            (By.ID, "lblNombreCompleto"),
            (By.XPATH, "//*[contains(translate(text(),'NOMBRE','nombre'),'nombre')]/following::td[1]"),
            (By.XPATH, "//*[contains(translate(text(),'NOMBRE','nombre'),'nombre')]/following::*[1]"),
        ]

        for by, selector in selectores:
            for elemento in self.driver.find_elements(by, selector):
                texto = elemento.text.strip()
                if texto and "nombre" not in texto.lower():
                    return texto

        return self._extraer_nombre_desde_texto()

    def _extraer_nombre_desde_texto(self) -> Optional[str]:
        assert self.driver is not None
        lineas_ignoradas = (
            "favor digitar",
            "debe utilizar",
            "tribunal supremo",
            "derechos reservados",
            "error de conexión",
            "inicio consultar",
            "consultar cédula",
            "consultar nombre",
        )

        for linea in self.driver.find_element(By.TAG_NAME, "body").text.splitlines():
            texto = linea.strip()
            if not texto:
                continue
            if any(ruido in texto.lower() for ruido in lineas_ignoradas):
                continue
            if len(texto.split()) >= 2 and not re.fullmatch(r"\d+", texto):
                return texto
        return None
