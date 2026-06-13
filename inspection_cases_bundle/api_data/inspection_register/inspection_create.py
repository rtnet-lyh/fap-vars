from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

import requests

from inspection_lookup import InspectionLookupClient, SESSION_COOKIE_NAME


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


def _compact_response(response: requests.Response) -> str:
    return str(getattr(response, "text", "") or "")[:4000]


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
                SESSION_COOKIE_NAME: jsessionid,
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
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(f"POST {path} HTTP {response.status_code}: {_compact_response(response)}") from exc
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


def _iter_md_paths(md_file: str | None, md_dir: str | None, *, recursive: bool) -> list[Path]:
    if md_file:
        return [Path(md_file).resolve()]
    if not md_dir:
        raise ValueError("--md-file 또는 --md-dir 중 하나를 지정해야 합니다.")

    base_dir = Path(md_dir).resolve()
    paths = base_dir.rglob("*.md") if recursive else base_dir.glob("*.md")
    excluded_parts = {"_reports", "_reference", "참고"}
    return sorted(
        path
        for path in paths
        if not any(part in excluded_parts for part in path.relative_to(base_dir).parts)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create inspection items from api_data/os Markdown files.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--md-file", help="Single api_data/os Markdown file to register.")
    target.add_argument("--md-dir", help="Directory containing api_data/os Markdown files.")
    parser.add_argument("--recursive", action="store_true", help="Read Markdown files recursively below --md-dir.")
    parser.add_argument("--execute", action="store_true", help="Send POST requests. Without this, only preview payloads.")
    parser.add_argument("--code", action="append", help="Limit to one inspection_code. Can be repeated.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    codes = set(args.code or [])
    try:
        md_paths = _iter_md_paths(args.md_file, args.md_dir, recursive=args.recursive)
        if not md_paths:
            raise ValueError("처리할 Markdown 파일이 없습니다.")

        created_or_ready = 0
        for md_path in md_paths:
            parsed = parse_api_data_md(md_path)
            if codes and parsed["inspection_code"] not in codes:
                continue
            client, _ = InspectionCreateClient.from_api_data_md(md_path)
            print(f"[LOOKUP] {parsed['inspection_code']} {md_path}", flush=True)
            payload = client.build_payload_from_md(md_path)
            print(f"[POST] {parsed['inspection_code']} {md_path} execute={args.execute}")
            if not args.execute:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                created_or_ready += 1
                continue

            result = client.create_from_md(md_path)
            print(f"[RESULT] {json.dumps(result, ensure_ascii=False)}")
            if result.get("status") != "success":
                raise RuntimeError(f"{parsed['inspection_code']} POST 응답 실패: {result}")
            created_or_ready += 1

        print(f"[SUMMARY] {json.dumps({'created_or_ready': created_or_ready}, ensure_ascii=False)}")
        return 0
    except Exception as exc:
        print(f"[FAILED] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
