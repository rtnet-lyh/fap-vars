from __future__ import annotations

import re
from pathlib import Path
from typing import Any


SECTION_PATTERN = re.compile(
    r"^#\s+(?P<title>.+?)\n(?P<body>.*?)(?=^#\s+.+?$|\Z)",
    re.MULTILINE | re.DOTALL,
)


REQUIRED_FIELDS = {
    "유형": "inspection_type",
    "분야": "area",
    "분류": "category",
    "OS/애플리케이션": "application_type",
    "제품명": "application",
    "코드": "inspection_code",
    "필수": "is_required",
    "점검항목명": "inspection_name",
    "점검 내용": "inspection_content",
    "점검명령어": "inspection_command",
    "출력 값": "inspection_output",
    "설명": "description",
    "기준치": "thresholds",
    "점검 스크립트": "inspection_script",
}


class MarkdownParseError(ValueError):
    pass


def _clean(text: str) -> str:
    return text.strip()


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```[^\n]*\n(?P<code>.*)\n```$", text, re.DOTALL)
    if match:
        return match.group("code").rstrip()
    return text


def _parse_required(value: str) -> int:
    return 1 if value.strip() == "필수" else 0


def _parse_thresholds(text: str) -> list[dict[str, Any]]:
    thresholds: list[dict[str, Any]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for sort_order, line in enumerate(lines):
        match = re.match(r"^-\s*`(?P<key>[^`]+)`\s*:\s*(?P<value>.+)$", line)
        if not match:
            continue

        raw_value = match.group("value").strip()
        if raw_value.startswith("`") and raw_value.endswith("`"):
            value = raw_value[1:-1]
        elif raw_value == "없음":
            value = ""
        else:
            value = raw_value

        thresholds.append(
            {
                "id": None,
                "key": match.group("key").strip(),
                "value": value.strip(),
                "sortOrder": sort_order,
            }
        )

    return thresholds


def _validate_sections(sections: dict[str, str]) -> None:
    missing = [title for title in REQUIRED_FIELDS if title not in sections or not sections[title].strip()]
    if missing:
        raise MarkdownParseError(f"필수 섹션이 없습니다: {missing}")


def parse_inspection_md(md_path: str | Path) -> dict[str, Any]:
    text = Path(md_path).read_text(encoding="utf-8")

    sections: dict[str, str] = {}
    for match in SECTION_PATTERN.finditer(text):
        title = _clean(match.group("title"))
        body = _clean(match.group("body"))
        sections[title] = body

    _validate_sections(sections)

    inspection_type = _clean(sections["유형"])
    if inspection_type != "일상점검(상태점검)":
        raise MarkdownParseError(
            f"유형 값은 '일상점검(상태점검)' 이어야 합니다. 현재 값: {inspection_type}"
        )

    parsed = {
        "inspection_type": inspection_type,
        "area": _clean(sections["분야"]),
        "category": _clean(sections["분류"]).lower(),
        "application_type": _clean(sections["OS/애플리케이션"]),
        "application": _clean(sections["제품명"]).lower(),
        "inspection_code": _clean(sections["코드"]),
        "is_required": _parse_required(sections["필수"]),
        "inspection_name": _clean(sections["점검항목명"]),
        "inspection_content": _clean(sections["점검 내용"]),
        "inspection_command": _strip_code_fence(sections["점검명령어"]),
        "inspection_output": _strip_code_fence(sections["출력 값"]),
        "description": _clean(sections["설명"]),
        "thresholds": _parse_thresholds(sections["기준치"]),
        "inspection_script": _strip_code_fence(sections["점검 스크립트"]),
    }

    if not parsed["thresholds"]:
        raise MarkdownParseError("기준치(thresholds)를 파싱하지 못했습니다.")

    return parsed
