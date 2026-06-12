#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests

API_DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXT_PATH = API_DATA_DIR / "api_context.md"
LEGACY_CONTEXT_PATH = API_DATA_DIR / "session.md"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def read_context_md(path: str | Path | None = None) -> dict[str, str]:
    """Read ## heading values from api_context.md.

    session.md is kept as a fallback only for older workspaces.
    """
    context_path = resolve_context_path(path)
    text = context_path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_key:
            values[current_key] = "\n".join(current_lines).strip()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            flush()
            current_key = match.group(1).strip()
            current_lines = []
            continue
        if current_key and line:
            current_lines.append(line)

    flush()
    return values


def resolve_context_path(path: str | Path | None = None) -> Path:
    if path:
        context_path = Path(path)
        if not context_path.is_absolute():
            context_path = Path.cwd() / context_path
        if not context_path.exists():
            raise ValueError(f"api context 파일이 없습니다: {context_path}")
        return context_path
    if DEFAULT_CONTEXT_PATH.exists():
        return DEFAULT_CONTEXT_PATH
    if LEGACY_CONTEXT_PATH.exists():
        return LEGACY_CONTEXT_PATH
    raise ValueError(f"api context 파일이 없습니다: {DEFAULT_CONTEXT_PATH}")


def require_context_value(context: dict[str, str], key: str, *, context_path: Path) -> str:
    value = str(context.get(key) or "").strip()
    if not value:
        raise ValueError(f"{context_path}에 {key} 값이 없습니다.")
    return value


def normalize_jsessionid(value: str | None) -> str:
    text = str(value or "").strip().strip('",')
    match = re.search(r"JSESSIONID=([^;\s,\"]+)", text)
    if match:
        return match.group(1)
    return text


def load_context_config(path: str | Path | None = None) -> dict[str, str]:
    context_path = resolve_context_path(path)
    context = read_context_md(context_path)
    host = require_context_value(context, "URL", context_path=context_path).rstrip("/")
    language = str(context.get("language") or "ko-KR").strip()
    jsessionid = normalize_jsessionid(context.get("JSESSIONID") or context.get("SESSION_ID"))
    if not jsessionid:
        raise ValueError(f"{context_path}에 SESSION_ID 또는 JSESSIONID 값이 없습니다.")

    return {
        "context_path": str(context_path),
        "host": host,
        "language": language,
        "jsessionid": jsessionid,
        "application_name": require_context_value(context, "application_name", context_path=context_path),
        "type_name": require_context_value(context, "type_name", context_path=context_path),
    }


def build_headers(config: dict[str, str]) -> dict[str, str]:
    host = config["host"]
    language = config["language"]
    jsessionid = config["jsessionid"]
    return {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": f"{language},ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Cookie": f"Language={language}; JSESSIONID={jsessionid}",
        "Referer": f"{host}/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
        "X-Requested-With": "XMLHttpRequest",
    }


SESSION = load_context_config()
HOST = SESSION["host"]
HEADERS = build_headers(SESSION)


def configure_context(path: str | Path | None = None) -> dict[str, str]:
    """Reload module-level API context for CLI callers and dependent tools."""
    global SESSION, HOST, HEADERS
    SESSION = load_context_config(path)
    HOST = SESSION["host"]
    HEADERS = build_headers(SESSION)
    return SESSION


def get_inspection_items() -> dict[str, Any]:
    """Fetch inspection item list filtered by type_name and application_name."""
    url = f"{HOST}/data/inspection/items"
    params = {
        "filterData": json.dumps([
            {"column": "type_name", "values": [SESSION["type_name"]]},
            {"column": "application_name", "values": [SESSION["application_name"]]},
        ], ensure_ascii=False),
        "selectStartRowNum": 0,
        "selectEndRowNum": 1000,
    }
    response = requests.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def get_item_detail(item_id: Any, mapping_id: Any) -> dict[str, Any]:
    """Fetch item detail and select the mapping matching mapping_id."""
    url = f"{HOST}/data/inspection/items/{item_id}"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()["data"]

    item_info = data["item"]
    target_mapping = next((m for m in data["mappings"] if str(m.get("id")) == str(mapping_id)), None)

    return {
        "item_id": item_id,
        "mapping_id": mapping_id,
        "type_name": item_info.get("type_name"),
        "category_name": item_info.get("category_name"),
        "area_name": item_info.get("area_name"),
        "code": item_info.get("code"),
        "inspection_code": item_info.get("inspection_code"),
        "inspection_name": item_info.get("inspection_name"),
        "inspection_content": item_info.get("inspection_content"),
        "application_type_name": (target_mapping or {}).get("application_type_name"),
        "application_name": (target_mapping or {}).get("application_name"),
        "application_version_name": (target_mapping or {}).get("application_version_name"),
        "inspection_command": (target_mapping or {}).get("inspection_command"),
        "inspection_output": (target_mapping or {}).get("inspection_output"),
        "description": (target_mapping or {}).get("description"),
        "inspection_script": (target_mapping or {}).get("inspection_script"),
    }


def get_item_thresholds(item_id: Any) -> list[dict[str, Any]]:
    """Fetch threshold information for an item."""
    url = f"{HOST}/data/inspection/items/{item_id}/thresholds"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()["data"]["thresholds"]


def sanitize_output_name(value: str) -> str:
    name = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", str(value or "").strip()).strip("_")
    return name or "inspection"


def default_output_path() -> Path:
    application_name = sanitize_output_name(SESSION["application_name"])
    return DEFAULT_OUTPUT_DIR / f"{application_name}_inspection_details.json"


def fetch_details(*, include_thresholds: bool = False) -> list[dict[str, Any]]:
    list_response = get_inspection_items()
    items = list_response["data"]["items"]
    print(f"총 {len(items)}개의 항목을 찾았습니다.")

    results: list[dict[str, Any]] = []
    for index, row in enumerate(items, start=1):
        item_id = row["item_id"]
        mapping_id = row["mapping_id"]
        print(f"항목 {index}/{len(items)} 처리 중: item_id={item_id}, mapping_id={mapping_id}")
        detail = get_item_detail(item_id, mapping_id)
        if include_thresholds:
            detail["thresholds"] = get_item_thresholds(item_id)
        results.append(detail)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch inspection item details by api_context.md type_name/application_name filters."
    )
    parser.add_argument("--context", help="Path to api_context.md. Defaults to api_data/api_context.md.")
    parser.add_argument("--output", help="Output JSON path. Defaults to outputs/<application_name>_inspection_details.json.")
    parser.add_argument("--include-thresholds", action="store_true", help="Also fetch /thresholds for each item.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        configure_context(args.context)
        output_path = Path(args.output) if args.output else default_output_path()
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print("목록 API 호출 중...")
        results = fetch_details(include_thresholds=args.include_thresholds)
        output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"결과가 {output_path}에 저장되었습니다.")
        for result in results[:5]:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("---")
        return 0
    except requests.exceptions.RequestException as exc:
        print(f"API 호출 오류: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"기타 오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
