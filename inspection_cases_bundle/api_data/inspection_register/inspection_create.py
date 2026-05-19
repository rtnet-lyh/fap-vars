from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

import requests

from inspection_lookup import InspectionLookupClient


REQUIRED_FIELDS = {
    "type_name",
    "area_name",
    "category_name",
    "application_type",
    "application",
    "inspection_code",
    "is_required",
    "inspection_name",
    "inspection_content",
    "inspection_command",
    "inspection_output",
    "description",
    "inspection_script",
}

SECTION_FIELDS = REQUIRED_FIELDS | {"thresholds"}


class ApiDataParseError(ValueError):
    pass


def _clean(text: str) -> str:
    return str(text or "").strip()


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```[^\n]*\n(?P<code>.*)\n```$", text, re.DOTALL)
    if match:
        return match.group("code").rstrip()
    return text


def _parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_title: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        if raw_line.startswith("# "):
            candidate = _clean(raw_line[2:])
            if candidate in SECTION_FIELDS:
                if current_title is not None:
                    sections[current_title] = "\n".join(current_lines).strip()
                current_title = candidate
                current_lines = []
                continue

        if current_title is not None:
            current_lines.append(raw_line)

    if current_title is not None:
        sections[current_title] = "\n".join(current_lines).strip()

    return sections


def _parse_required(text: str) -> int:
    return 1 if _clean(text) == "필수" else 0


def _parse_thresholds(text: str) -> list[dict[str, Any]]:
    thresholds: list[dict[str, Any]] = []
    pattern = re.compile(
        r"\{id:\s*(?P<id>null|\d+),\s*key:\s*\"(?P<key>[^\"]+)\",\s*value:\s*\"(?P<value>[^\"]*)\",\s*sortOrder:\s*(?P<sort>\d+)\}",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        raw_id = match.group("id")
        thresholds.append(
            {
                "id": None if raw_id == "null" else int(raw_id),
                "key": match.group("key").strip(),
                "value": match.group("value").strip(),
                "sortOrder": int(match.group("sort")),
            }
        )
    return thresholds


def parse_api_data_md(md_path: str | Path) -> dict[str, Any]:
    text = Path(md_path).read_text(encoding="utf-8")
    sections = _parse_sections(text)

    missing_fields = [field for field in REQUIRED_FIELDS if not _clean(sections.get(field, ""))]
    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))
        raise ApiDataParseError(f"{missing_text} 값이 없습니다.")

    thresholds = _parse_thresholds(sections.get("thresholds", ""))

    return {
        "inspection_type": _clean(sections["type_name"]),
        "area": _clean(sections["area_name"]),
        "category": _clean(sections["category_name"]),
        "application_type": _clean(sections["application_type"]),
        "application": _clean(sections["application"]),
        "inspection_code": _clean(sections["inspection_code"]),
        "is_required": _parse_required(sections["is_required"]),
        "inspection_name": _clean(sections["inspection_name"]),
        "inspection_content": _clean(sections["inspection_content"]),
        "inspection_command": _strip_code_fence(sections["inspection_command"]),
        "inspection_output": _strip_code_fence(sections["inspection_output"]),
        "description": _clean(sections["description"]),
        "thresholds": thresholds,
        "inspection_script": sections["inspection_script"].rstrip(),
    }


class InspectionCreateClient:
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
        self.lookup = InspectionLookupClient(base_url, jsessionid, language)

    @classmethod
    def from_api_data_md(cls, md_path: str | Path) -> tuple["InspectionCreateClient", dict[str, Any]]:
        session_config = InspectionLookupClient._load_session_config(md_path)
        client = cls(
            base_url=session_config["base_url"],
            jsessionid=session_config["jsessionid"],
            language=session_config["language"],
        )
        parsed = parse_api_data_md(md_path)
        return client, parsed

    @staticmethod
    def build_revision_num() -> int:
        today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
        return int(f"{today}01")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(f"{self.base_url}{path}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def build_payload_from_md(
        self,
        md_path: str | Path,
        *,
        application_family_id: int | None = None,
        application_version_id: int | None = None,
        is_fix: bool = False,
    ) -> dict[str, Any]:
        parsed = parse_api_data_md(md_path)
        resolved = self.lookup.resolve_ids(
            inspection_type=parsed["inspection_type"],
            area=parsed["area"],
            category=parsed["category"],
            application_type=parsed["application_type"],
            application=parsed["application"],
        )

        return {
            "type_id": resolved["type_id"],
            "type_name": resolved["type_name"],
            "area_id": resolved["area_id"],
            "area_name": resolved["area_name"],
            "category_id": resolved["category_id"],
            "category_name": resolved["category_name"],
            "application_type_id": resolved["application_type_id"],
            "application_type_name": resolved["application_type_name"],
            "application_id": resolved["application_id"],
            "application_name": resolved["application_name"],
            "application_family_id": application_family_id,
            "application_version_id": application_version_id,
            "inspection_code": parsed["inspection_code"],
            "inspection_name": parsed["inspection_name"],
            "inspection_content": parsed["inspection_content"],
            "inspection_command": parsed["inspection_command"],
            "inspection_output": parsed["inspection_output"],
            "description": parsed["description"],
            "inspection_script": parsed["inspection_script"],
            "is_required": parsed["is_required"],
            "is_fix": is_fix,
            "revision_num": self.build_revision_num(),
            "thresholds": parsed["thresholds"],
        }

    @classmethod
    def build_payload_directly_from_md(
        cls,
        md_path: str | Path,
        *,
        application_family_id: int | None = None,
        application_version_id: int | None = None,
        is_fix: bool = False,
    ) -> dict[str, Any]:
        client, _ = cls.from_api_data_md(md_path)
        return client.build_payload_from_md(
            md_path,
            application_family_id=application_family_id,
            application_version_id=application_version_id,
            is_fix=is_fix,
        )

    def create_from_md(
        self,
        md_path: str | Path,
        *,
        application_family_id: int | None = None,
        application_version_id: int | None = None,
        is_fix: bool = False,
    ) -> dict[str, Any]:
        payload = self.build_payload_from_md(
            md_path,
            application_family_id=application_family_id,
            application_version_id=application_version_id,
            is_fix=is_fix,
        )
        return self._post("/data/inspection/items", payload)


if __name__ == "__main__":
    import sys
    import os

    base_dir = Path(__file__).resolve().parents[1] / "os" / "solaris"
    md_files = [f for f in os.listdir(base_dir) if f.endswith('.md')]

    for md_file in md_files:
        md_path = base_dir / md_file
        print(f"Processing {md_file}...")
        try:
            client, _ = InspectionCreateClient.from_api_data_md(md_path)
            payload = client.build_payload_from_md(md_path)
            print("[PAYLOAD PREVIEW]")
            print(payload)

            # 실제 등록 시 아래 주석 해제
            result = client.create_from_md(md_path)
            print("[RESULT]")
            print(result)
        except Exception as e:
            print(f"Error processing {md_file}: {e}")
        print("-" * 50)
