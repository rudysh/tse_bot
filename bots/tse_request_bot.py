import re
from html import unescape
from typing import Optional
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class TseRequestBot:
    """Consulta cédulas mediante requests simulando el formulario ASP.NET."""

    metodo = "api_request"

    def __init__(self, url: str, logger) -> None:
        self.url = url
        self.logger = logger
        self.session: Optional[requests.Session] = None
        parsed = urlparse(url)
        self.origin = f"{parsed.scheme}://{parsed.netloc}"

    def abrir(self) -> None:
        self.session = requests.Session()

    def cerrar(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None

    def consultar_cedula(self, cedula: str) -> tuple[str, str]:
        if self.session is None:
            raise RuntimeError("La sesión HTTP no está abierta")

        try:
            respuesta_get = self.session.get(self.url, headers=self._headers_get(), timeout=20)
            respuesta_get.raise_for_status()
            campos_ocultos = self._extraer_campos_ocultos(respuesta_get.text)

            payload = {
                **campos_ocultos,
                "ScriptManager1": "UpdatePanel1|btnConsultaCedula",
                "txtcedula": cedula,
                "grupo": "",
                "comentario": "",
                "__ASYNCPOST": "true",
                "btnConsultaCedula": "Consultar",
            }
            respuesta_post = self.session.post(
                self.url,
                data=payload,
                headers=self._headers_post(),
                timeout=20,
            )
            respuesta_post.raise_for_status()
            contenido_resultado = self._resolver_contenido_resultado(respuesta_post)
            return self._leer_resultado(contenido_resultado)
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Fallo consultando cédula %s por api_request", cedula)
            return "", f"Error: {exc}"

    def _extraer_campos_ocultos(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        campos = {}
        for nombre in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
            campo = soup.find("input", {"name": nombre})
            if campo is None or campo.get("value") is None:
                raise RuntimeError(f"No se encontró el campo oculto {nombre}")
            campos[nombre] = campo["value"]
        return campos

    def _leer_resultado(self, contenido: str) -> tuple[str, str]:
        contenido_util = self._extraer_contenido_util(contenido)
        texto = BeautifulSoup(contenido_util, "html.parser").get_text(" ", strip=True)
        texto_normalizado = texto.lower()

        if "error de conexión" in texto_normalizado:
            raise RuntimeError("El sitio del TSE mostró error de conexión")
        if "no se encontró" in texto_normalizado or "no existe" in texto_normalizado:
            return "", "No encontrado"

        nombre = self._extraer_nombre(contenido_util)
        if nombre:
            return nombre, "Consultado"
        return "", "Sin nombre detectado"

    def _resolver_contenido_resultado(self, respuesta_post: requests.Response) -> str:
        contenido = respuesta_post.text
        destino = self._extraer_redireccion_ajax(contenido)
        if destino:
            assert self.session is not None
            url_destino = urljoin(self.url, unquote(destino))
            respuesta_resultado = self.session.get(
                url_destino,
                headers=self._headers_get(),
                timeout=20,
            )
            respuesta_resultado.raise_for_status()
            return respuesta_resultado.text

        return contenido

    @staticmethod
    def _extraer_redireccion_ajax(contenido: str) -> Optional[str]:
        patrones = (
            r"pageRedirect\|\|([^|]+)\|",
            r"resultado_persona\.aspx[^|\"']*",
        )
        for patron in patrones:
            coincidencia = re.search(patron, contenido, flags=re.IGNORECASE)
            if coincidencia:
                return coincidencia.group(1) if coincidencia.groups() else coincidencia.group(0)
        return None

    @staticmethod
    def _extraer_contenido_util(contenido: str) -> str:
        """Extrae el HTML útil cuando ASP.NET devuelve una respuesta delta."""
        if "|updatePanel|" not in contenido:
            return contenido

        partes = contenido.split("|")
        fragmentos_html: list[str] = []
        for indice, parte in enumerate(partes):
            if parte == "updatePanel" and indice + 2 < len(partes):
                fragmentos_html.append(unescape(partes[indice + 2]))

        return "\n".join(fragmentos_html) if fragmentos_html else contenido

    def _extraer_nombre(self, contenido: str) -> Optional[str]:
        soup = BeautifulSoup(contenido, "html.parser")
        for selector in ("#lblNombre", "#lblNombreCompleto", "#lblnombrecompleto"):
            elemento = soup.select_one(selector)
            if elemento:
                texto = elemento.get_text(" ", strip=True)
                if texto:
                    return texto

        texto = soup.get_text("\n", strip=True)
        return self._extraer_nombre_desde_texto(texto)

    @staticmethod
    def _extraer_nombre_desde_texto(texto: str) -> Optional[str]:
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

        for linea in texto.splitlines():
            valor = linea.strip()
            if not valor:
                continue
            if any(ruido in valor.lower() for ruido in lineas_ignoradas):
                continue
            if len(valor.split()) >= 2 and not re.fullmatch(r"\d+", valor):
                return valor
        return None

    def _headers_get(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent(),
            "Referer": self.url,
        }

    def _headers_post(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent(),
            "Referer": self.url,
            "Origin": self.origin,
            "X-MicrosoftAjax": "Delta=true",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

    @staticmethod
    def _user_agent() -> str:
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
