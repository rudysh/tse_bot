import re
from html import unescape
from typing import Optional
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class TseRequestBot:
    """Queries IDs through requests by simulating the ASP.NET form."""

    method = "api_request"

    def __init__(self, url: str, logger) -> None:
        self.url = url
        self.logger = logger
        self.session: Optional[requests.Session] = None
        parsed_url = urlparse(url)
        self.origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

    def open(self) -> None:
        self.session = requests.Session()

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None

    def query_id(self, id_number: str) -> tuple[str, str]:
        if self.session is None:
            raise RuntimeError("La sesión HTTP no está abierta")

        try:
            get_response = self.session.get(self.url, headers=self._get_headers(), timeout=20)
            get_response.raise_for_status()
            hidden_fields = self._extract_hidden_fields(get_response.text)

            payload = {
                **hidden_fields,
                "ScriptManager1": "UpdatePanel1|btnConsultaCedula",
                "txtcedula": id_number,
                "grupo": "",
                "comentario": "",
                "__ASYNCPOST": "true",
                "btnConsultaCedula": "Consultar",
            }
            post_response = self.session.post(
                self.url,
                data=payload,
                headers=self._post_headers(),
                timeout=20,
            )
            post_response.raise_for_status()
            result_content = self._resolve_result_content(post_response)
            return self._read_result(result_content)
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Fallo consultando cédula %s por api_request", id_number)
            return "", f"Error: {exc}"

    def _extract_hidden_fields(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        fields = {}
        for field_name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
            field = soup.find("input", {"name": field_name})
            if field is None or field.get("value") is None:
                raise RuntimeError(f"No se encontró el campo oculto {field_name}")
            fields[field_name] = field["value"]
        return fields

    def _read_result(self, content: str) -> tuple[str, str]:
        useful_content = self._extract_useful_content(content)
        text = BeautifulSoup(useful_content, "html.parser").get_text(" ", strip=True)
        normalized_text = text.lower()

        if "error de conexión" in normalized_text:
            raise RuntimeError("El sitio del TSE mostró error de conexión")
        if "no se encontró" in normalized_text or "no existe" in normalized_text:
            return "", "No encontrado"

        name = self._extract_name(useful_content)
        if name:
            return name, "Consultado"
        return "", "Sin nombre detectado"

    def _resolve_result_content(self, post_response: requests.Response) -> str:
        content = post_response.text
        redirect_target = self._extract_ajax_redirect(content)
        if redirect_target:
            assert self.session is not None
            redirect_url = urljoin(self.url, unquote(redirect_target))
            result_response = self.session.get(
                redirect_url,
                headers=self._get_headers(),
                timeout=20,
            )
            result_response.raise_for_status()
            return result_response.text

        return content

    @staticmethod
    def _extract_ajax_redirect(content: str) -> Optional[str]:
        patterns = (
            r"pageRedirect\|\|([^|]+)\|",
            r"resultado_persona\.aspx[^|\"']*",
        )
        for pattern in patterns:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return None

    @staticmethod
    def _extract_useful_content(content: str) -> str:
        """Extracts useful HTML when ASP.NET returns a delta response."""
        if "|updatePanel|" not in content:
            return content

        parts = content.split("|")
        html_fragments: list[str] = []
        for index, part in enumerate(parts):
            if part == "updatePanel" and index + 2 < len(parts):
                html_fragments.append(unescape(parts[index + 2]))

        return "\n".join(html_fragments) if html_fragments else content

    def _extract_name(self, content: str) -> Optional[str]:
        soup = BeautifulSoup(content, "html.parser")
        for selector in ("#lblNombre", "#lblNombreCompleto", "#lblnombrecompleto"):
            element = soup.select_one(selector)
            if element:
                text = element.get_text(" ", strip=True)
                if text:
                    return text

        text = soup.get_text("\n", strip=True)
        return self._extract_name_from_text(text)

    @staticmethod
    def _extract_name_from_text(text: str) -> Optional[str]:
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

        for line in text.splitlines():
            value = line.strip()
            if not value:
                continue
            if any(noise in value.lower() for noise in ignored_lines):
                continue
            if len(value.split()) >= 2 and not re.fullmatch(r"\d+", value):
                return value
        return None

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent(),
            "Referer": self.url,
        }

    def _post_headers(self) -> dict[str, str]:
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
