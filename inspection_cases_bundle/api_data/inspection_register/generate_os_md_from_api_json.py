#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import pathlib
import re
from typing import Any

BASE_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = BASE_DIR / "outputs"
DEFAULT_OUTPUT_ROOT = BASE_DIR.parent / "os"
CASE_NAME_RE = re.compile(r"case_name\s*[:=]\s*['\"]([\w_-]+)['\"]")


def normalize_newlines(text: Any) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def sanitize_path_part(value: Any, fallback: str = "unknown") -> str:
    sanitized = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", str(value or "").strip()).strip("_")
    return sanitized or fallback


def sanitize_filename(name: Any) -> str:
    return sanitize_path_part(name, fallback="item")


def extract_case_name(script: str, inspection_code: str, inspection_name: str) -> str:
    match = CASE_NAME_RE.search(script)
    if match:
        return match.group(1)
    code_part = sanitize_filename(str(inspection_code or "").lower())
    name_part = sanitize_filename(inspection_name)
    parts = [part for part in (code_part, name_part) if part]
    base_name = "_".join(parts) if parts else "item"
    if base_name.endswith("_check"):
        return base_name
    return f"{base_name}_check"


def pick_first(item: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def require_value(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} 값이 없습니다.")
    return text


def normalize_required(value: Any) -> str:
    if isinstance(value, bool):
        return "필수" if value else "선택"
    text = str(value or "").strip()
    if text in {"1", "true", "True", "필수"}:
        return "필수"
    if text in {"0", "false", "False", "선택"}:
        return "선택"
    return text or "선택"


def format_thresholds(item: dict[str, Any]) -> str:
    thresholds = item.get("thresholds") or []
    if not isinstance(thresholds, list) or not thresholds:
        return "[]"

    lines = ["["]
    written_count = 0
    for threshold in thresholds:
        if not isinstance(threshold, dict):
            continue
        key = pick_first(threshold, "key", "name")
        value = pick_first(threshold, "value", "value1")
        raw_id = threshold.get("id")
        id_text = "null" if raw_id in (None, "") else str(raw_id)
        sort_order = threshold.get("sortOrder", threshold.get("sort_order", written_count))
        comma = "," if written_count > 0 else ""
        lines.append(
            f'{comma}    {{id: {id_text}, key: "{escape_js_string(key)}", '
            f'value: "{escape_js_string(value)}", sortOrder: {sort_order}}}'
        )
        written_count += 1
    lines.append("]")
    return "\n".join(lines)


def escape_js_string(value: Any) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def build_md(item: dict[str, Any], *, application_type: str = "") -> str:
    inspection_command = normalize_newlines(item.get("inspection_command")).strip()
    inspection_output = normalize_newlines(item.get("inspection_output")).strip()
    description = normalize_newlines(item.get("description")).strip()
    script = normalize_newlines(item.get("inspection_script")).rstrip()

    application_type_name = pick_first(item, "application_type_name", "application_type", default=application_type)
    values = [
        ("type_name", require_value(pick_first(item, "type_name"), "type_name")),
        ("area_name", require_value(pick_first(item, "area_name"), "area_name")),
        ("category_name", require_value(pick_first(item, "category_name"), "category_name")),
        ("application_type", require_value(application_type_name, "application_type")),
        ("application", require_value(pick_first(item, "application_name", "application"), "application")),
        ("inspection_code", require_value(pick_first(item, "inspection_code"), "inspection_code")),
        ("is_required", normalize_required(item.get("is_required"))),
        ("inspection_name", require_value(pick_first(item, "inspection_name"), "inspection_name")),
        ("inspection_content", require_value(pick_first(item, "inspection_content"), "inspection_content")),
    ]
    require_value(inspection_command, "inspection_command")
    require_value(inspection_output, "inspection_output")
    require_value(description, "description")
    require_value(script, "inspection_script")

    chunks = [f"# {heading}\n\n{value}".rstrip() for heading, value in values]
    chunks.append(f"# inspection_command\n\n```bash\n{inspection_command}\n```")
    chunks.append(f"# inspection_output\n\n```text\n{inspection_output}\n```")
    chunks.append(f"# description\n\n{description}".rstrip())
    chunks.append(f"# thresholds\n\n{format_thresholds(item)}")
    chunks.append(f"# inspection_script\n\n{script}")
    return "\n\n".join(chunks).rstrip() + "\n"


def output_path_for_item(item: dict[str, Any], output_root: pathlib.Path, *, application_type: str = "") -> pathlib.Path:
    category_name = sanitize_path_part(require_value(pick_first(item, "category_name"), "category_name"), fallback="category")
    application_type_name = sanitize_path_part(
        require_value(pick_first(item, "application_type_name", "application_type", default=application_type), "application_type"),
        fallback="application_type",
    )
    application_name = sanitize_path_part(
        require_value(pick_first(item, "application_name", "application"), "application"),
        fallback="application",
    )
    script = normalize_newlines(item.get("inspection_script"))
    case_name = extract_case_name(script, pick_first(item, "inspection_code"), pick_first(item, "inspection_name"))
    return output_root / category_name / application_type_name / application_name / f"{case_name}.md"


def load_items(input_path: pathlib.Path) -> list[dict[str, Any]]:
    if input_path.is_dir():
        json_files = sorted(input_path.glob("*.json"))
        items: list[dict[str, Any]] = []
        for json_file in json_files:
            items.extend(load_items(json_file))
        return items

    data = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        raw_items = data.get("items") or data.get("data") or [data]
        if isinstance(raw_items, list):
            return [item for item in raw_items if isinstance(item, dict)]
    raise ValueError(f"지원하지 않는 JSON 구조입니다: {input_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate api_data/os Markdown files from fetched inspection detail JSON."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Input JSON file or directory.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="api_data/os output root.")
    parser.add_argument("--application-type", default="", help="Fallback application_type when JSON does not include it.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing Markdown files.")
    parser.add_argument("--dry-run", action="store_true", help="Print target paths without writing files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = pathlib.Path(args.input)
    output_root = pathlib.Path(args.output_root)
    items = load_items(input_path)
    created = []
    skipped = []

    for item in items:
        output_path = output_path_for_item(item, output_root, application_type=args.application_type)
        if output_path.exists() and not args.overwrite:
            skipped.append(str(output_path))
            continue
        if not args.dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(build_md(item, application_type=args.application_type), encoding="utf-8")
        created.append(str(output_path))

    print(json.dumps({"created": created, "skipped": skipped, "dry_run": args.dry_run}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
