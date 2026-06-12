from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests


SECTION_PATTERN = re.compile(
    r"^#\s+(?P<title>.+?)\n(?P<body>.*?)(?=^#\s+.+?$|\Z)",
    re.MULTILINE | re.DOTALL,
)

SESSION_PATTERN = re.compile(
    r"^##\s+(?P<title>.+?)\n(?P<body>.*?)(?=^##\s+.+?$|\Z)",
    re.MULTILINE | re.DOTALL,
)

LOOKUP_MD_FIELDS = {
    "type_name": "inspection_type",
    "area_name": "area",
    "category_name": "category",
    "application_type": "application_type",
    "application": "application",
}

CATEGORY_RETRY_ALIASES = {
    "log": ["로그"],
    "kernal": ["커널"],
    "kernel": ["커널"],
}


def _clean(text: str) -> str:
    return str(text or "").strip()


def _parse_markdown_sections(text: str, pattern: re.Pattern[str]) -> dict[str, str]:
    sections: dict[str, str] = {}
    for match in pattern.finditer(text):
        title = _clean(match.group("title"))
        body = _clean(match.group("body"))
        sections[title] = body
    return sections




def _find_api_data_dir(path: Path) -> Path:
    for parent in path.resolve().parents:
        if parent.name == "api_data":
            return parent
    raise ValueError(f"api_data 디렉터리를 찾지 못했습니다: {path}")


def _resolve_context_path(api_data_dir: Path) -> Path:
    context_path = api_data_dir / "api_context.md"
    if context_path.exists():
        return context_path
    legacy_path = api_data_dir / "session.md"
    if legacy_path.exists():
        return legacy_path
    raise ValueError(f"api_context.md 파일이 없습니다: {context_path}")



def _normalize_jsessionid(value: str) -> str:
    text = str(value or "").strip().strip('",')
    match = re.search(r"JSESSIONID=([^;\s,\"]+)", text)
    if match:
        return match.group(1)
    return text

def _extract_available_values_from_error(message: str) -> list[str]:
    match = re.search(r"가능한 값:\s*\[(?P<values>.*)\]\s*$", str(message or ""))
    if not match:
        return []
    raw_values = match.group("values")
    return [value.strip().strip("'\"") for value in raw_values.split(",") if value.strip()]


class InspectionLookupClient:
    def __init__(self, base_url: str, jsessionid: str, language: str = "ko-KR"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/json",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/147.0.0.0 Safari/537.36"
                ),
            }
        )
        self.session.cookies.update(
            {
                "JSESSIONID": jsessionid,
                "Language": language,
            }
        )

    @staticmethod
    def _load_lookup_names_from_md(md_path: str | Path) -> dict[str, str]:
        md_file = Path(md_path)
        text = md_file.read_text(encoding="utf-8")
        sections = _parse_markdown_sections(text, SECTION_PATTERN)

        resolved: dict[str, str] = {}
        missing_fields: list[str] = []

        for md_key, output_key in LOOKUP_MD_FIELDS.items():
            raw_value = sections.get(md_key, "")
            value = _clean(raw_value)
            if not value:
                missing_fields.append(md_key)
                continue
            resolved[output_key] = value

        if missing_fields:
            missing_text = ", ".join(missing_fields)
            raise ValueError(f"{missing_text} 값이 없습니다.")

        return resolved

    @staticmethod
    def _load_session_config(md_path: str | Path) -> dict[str, str]:
        md_file = Path(md_path).resolve()
        api_data_dir = _find_api_data_dir(md_file)
        context_path = _resolve_context_path(api_data_dir)

        sections = _parse_markdown_sections(context_path.read_text(encoding="utf-8"), SESSION_PATTERN)

        session_id = _normalize_jsessionid(_clean(sections.get("SESSION_ID", "") or sections.get("JSESSIONID", "")))
        base_url = _clean(sections.get("URL", ""))
        language = _clean(sections.get("language", "")) or "ko-KR"

        if not session_id:
            raise ValueError("SESSION_ID 또는 JSESSIONID 값이 없습니다.")
        if not base_url:
            raise ValueError("URL 값이 없습니다.")

        return {
            "base_url": base_url.rstrip("/"),
            "jsessionid": session_id,
            "language": language,
            "context_path": str(context_path),
        }

    @classmethod
    def from_api_data_md(cls, md_path: str | Path) -> tuple["InspectionLookupClient", dict[str, str]]:
        lookup_names = cls._load_lookup_names_from_md(md_path)
        session_config = cls._load_session_config(md_path)
        client = cls(
            base_url=session_config["base_url"],
            jsessionid=session_config["jsessionid"],
            language=session_config["language"],
        )
        return client, lookup_names

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _find_by_name(
        items: list[dict[str, Any]],
        name: str,
        *,
        id_key: str = "id",
        name_key: str = "name",
    ) -> int:
        target = str(name).strip().lower()

        for item in items:
            current = str(item.get(name_key, "")).strip().lower()
            if current == target:
                return int(item[id_key])

        available = [item.get(name_key) for item in items]
        raise ValueError(f"'{name}' 을(를) 찾지 못했습니다. 가능한 값: {available}")

    def get_type_id(self, inspection_type: str) -> int:
        data = self._get("/data/inspection/category/types")
        return self._find_by_name(data["data"]["types"], inspection_type)

    def get_area_id(self, type_id: int, area: str) -> int:
        data = self._get(f"/data/inspection/areas/{type_id}")
        return self._find_by_name(data["data"]["areas"], area)

    def get_category_id(self, area_id: int, type_id: int, category: str) -> int:
        data = self._get(
            f"/data/inspection/category/{area_id}",
            params={"categoryTypeId": type_id},
        )
        return self._find_by_name(data["data"]["categories"], category)

    def get_category_id_with_retry(self, area_id: int, type_id: int, category: str) -> tuple[int, str]:
        try:
            return self.get_category_id(area_id, type_id, category), category
        except ValueError as exc:
            available_values = _extract_available_values_from_error(str(exc))
            retry_candidates = CATEGORY_RETRY_ALIASES.get(str(category or "").strip().lower(), [])
            normalized_available = {value.strip().lower(): value for value in available_values}

            for candidate in retry_candidates:
                resolved_candidate = normalized_available.get(candidate.strip().lower())
                if not resolved_candidate:
                    continue
                return self.get_category_id(area_id, type_id, resolved_candidate), resolved_candidate

            raise

    def get_application_type_id(self, application_type: str) -> int:
        data = self._get("/data/inspection/application/types")
        return self._find_by_name(data["data"]["types"], application_type)

    def get_application_id(self, application_type_id: int, application: str) -> int:
        data = self._get(
            "/data/inspection/applications",
            params={"typeId": application_type_id},
        )
        return self._find_by_name(data["data"]["applications"], application)

    def resolve_ids(
        self,
        *,
        inspection_type: str,
        area: str,
        category: str,
        application_type: str,
        application: str,
    ) -> dict[str, Any]:
        type_id = self.get_type_id(inspection_type)
        area_id = self.get_area_id(type_id, area)
        category_id, resolved_category = self.get_category_id_with_retry(area_id, type_id, category)
        application_type_id = self.get_application_type_id(application_type)
        application_id = self.get_application_id(application_type_id, application)

        return {
            "type_id": type_id,
            "type_name": inspection_type,
            "area_id": area_id,
            "area_name": area,
            "category_id": category_id,
            "category_name": resolved_category,
            "application_type_id": application_type_id,
            "application_type_name": application_type,
            "application_id": application_id,
            "application_name": application,
        }

    @classmethod
    def resolve_ids_from_md(cls, md_path: str | Path) -> dict[str, Any]:
        client, lookup_names = cls.from_api_data_md(md_path)
        return client.resolve_ids(
            inspection_type=lookup_names["inspection_type"],
            area=lookup_names["area"],
            category=lookup_names["category"],
            application_type=lookup_names["application_type"],
            application=lookup_names["application"],
        )


if __name__ == "__main__":
    default_md = (
        Path(__file__).resolve().parents[1]
        / "os"
        / "solaris"
        / "solaris_memory_recognition_prtdiag_check.md"
    )
    print(InspectionLookupClient.resolve_ids_from_md(default_md))
