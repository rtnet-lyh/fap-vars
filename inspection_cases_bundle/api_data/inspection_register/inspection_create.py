from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import json
from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Any
from zoneinfo import ZoneInfo

import requests

from inspection_lookup import InspectionLookupClient, SESSION_COOKIE_NAME
from seed_inspection_values import main as seed_inspection_values_main


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

FALLBACK_FIELD_ALIASES = {
    "type_name": ("type_name", "유형"),
    "area_name": ("area_name", "분야"),
    "category_name": ("category_name", "분류", "영역"),
    "application_type": ("application_type", "OS/애플리케이션"),
    "application": ("application", "제품명"),
    "inspection_code": ("inspection_code", "코드"),
    "is_required": ("is_required", "필수", "구분"),
    "inspection_name": ("inspection_name", "점검항목명", "세부 점검항목", "세부 점검 항목"),
    "inspection_content": ("inspection_content", "점검 내용"),
    "inspection_command": ("inspection_command", "점검명령어", "점검 명령어", "명령어"),
    "inspection_output": ("inspection_output", "출력 값", "출력 결과"),
    "description": ("description", "설명"),
    "inspection_script": ("inspection_script", "점검 스크립트"),
    "thresholds": ("thresholds", "기준치", "임계치"),
}

RAW_HEADING_PATTERN = re.compile(
    r"^\ufeff?#\s+(?P<title>.+?)\n(?P<body>.*?)(?=^\ufeff?#\s+.+?$|\Z)",
    re.MULTILINE | re.DOTALL,
)

PLATFORM_APPLICATION_NAMES = {
    "aix",
    "esxi",
    "hpux",
    "linux",
    "rocky",
    "solaris",
    "unix",
    "windows",
    "windows2019",
}

PRODUCT_APPLICATION_AREAS = {"dbms", "was", "web"}

APPLICATION_NAME_ALIASES = {
    "apache_tomcat": ("Apache Tomcat", "apache_tomcat"),
    "jeus": ("JEUS", "jeus"),
    "oracle": ("oracle", "Oracle"),
    "webtob": ("WebtoB", "webtob"),
}

SEARCH_TARGET = (
    "inspection_code,cve_id,type_name,area_name,category_name,"
    "application_type_name,application_name,application_family_name,"
    "application_version_name,is_required,inspection_name,inspection_content,modified_at"
)


class ApiDataParseError(ValueError):
    pass


class InspectionMetadataSeedError(RuntimeError):
    pass


class _Tee:
    def __init__(self, *streams: Any):
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def _clean(text: str) -> str:
    return str(text or "").strip()


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```[^\n]*\n(?P<code>.*?)(?:\n```|\Z)", text, re.DOTALL)
    if match:
        return match.group("code").rstrip()
    return text


def _field_has_value(field: str, value: str) -> bool:
    if field in {"inspection_command", "inspection_output", "inspection_script"}:
        return bool(_clean(_strip_code_fence(value)))
    return bool(_clean(value))


def _compact_response(response: requests.Response) -> str:
    return str(getattr(response, "text", "") or "")[:4000]


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold()


def _existing_item_key(code: Any, application: Any) -> tuple[str, str]:
    return (_normalize_key(code), _normalize_key(application))


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_key(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


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


def _parse_all_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for match in RAW_HEADING_PATTERN.finditer(text):
        title = _clean(match.group("title"))
        body = match.group("body").strip()
        sections[title] = body
    return sections


def _section_by_alias(sections: dict[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        if _clean(sections.get(alias, "")):
            return sections[alias]

    for title, body in sections.items():
        clean_title = _clean(title)
        for alias in aliases:
            if clean_title.startswith(f"{alias} ") and _clean(body):
                return body
    return ""


def _parse_fallback_sections(text: str) -> dict[str, str]:
    raw_sections = _parse_all_sections(text)
    sections: dict[str, str] = {}

    for target, aliases in FALLBACK_FIELD_ALIASES.items():
        value = _section_by_alias(raw_sections, aliases)
        if value:
            sections[target] = value

    description_parts = [
        _clean(_section_by_alias(raw_sections, ("설명", "description"))),
        _clean(_section_by_alias(raw_sections, ("판단기준", "판단 기준"))),
    ]
    description = "\n\n".join(part for part in description_parts if part)
    if description:
        sections["description"] = description

    return sections


def _find_api_data_os_dir(path: Path) -> Path | None:
    resolved = path.resolve()
    for parent in (resolved.parent, *resolved.parents):
        if parent.name == "os" and parent.parent.name == "api_data":
            return parent
    return None


def _relative_api_data_os_path(path: Path) -> Path | None:
    os_dir = _find_api_data_os_dir(path)
    if os_dir is None:
        return None
    return path.resolve().relative_to(os_dir)


def _matching_raw_data_path(md_path: str | Path) -> Path | None:
    path = Path(md_path).resolve()
    rel_path = _relative_api_data_os_path(path)
    os_dir = _find_api_data_os_dir(path)
    if rel_path is None or os_dir is None:
        return None

    raw_path = os_dir.parent.parent / "raw_data" / rel_path
    return raw_path if raw_path.exists() else None


def _matching_case_json_path(md_path: str | Path) -> Path | None:
    path = Path(md_path).resolve()
    rel_path = _relative_api_data_os_path(path)
    os_dir = _find_api_data_os_dir(path)
    if rel_path is None or os_dir is None:
        return None

    case_json_path = os_dir.parent.parent / "inspection_cases" / rel_path.with_suffix("") / "case.json"
    return case_json_path if case_json_path.exists() else None


def _first_case_item(case_data: dict[str, Any]) -> dict[str, Any]:
    item = case_data.get("item")
    if isinstance(item, dict):
        return item

    items = case_data.get("items")
    if isinstance(items, list):
        for candidate in items:
            if isinstance(candidate, dict):
                return candidate
    return {}


def _fallback_sections_from_case_json(case_json_path: Path) -> dict[str, str]:
    try:
        data = json.loads(case_json_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}

    item = _first_case_item(data)
    sections: dict[str, str] = {}
    direct_mappings = {
        "inspection_code": ("inspection_code",),
        "inspection_name": ("inspection_name", "inspection_item_name"),
        "inspection_content": ("inspection_content",),
        "inspection_command": ("inspection_command",),
        "description": ("description", "action_content"),
        "is_required": ("is_required",),
    }
    for target, keys in direct_mappings.items():
        for source in (item, data):
            if not isinstance(source, dict):
                continue
            for key in keys:
                value = _clean(source.get(key, ""))
                if value:
                    sections[target] = value
                    break
            if target in sections:
                break

    threshold_list = item.get("threshold_list")
    if isinstance(threshold_list, list):
        thresholds = []
        for index, threshold in enumerate(threshold_list):
            if not isinstance(threshold, dict):
                continue
            key = _clean(threshold.get("name") or threshold.get("key"))
            if not key:
                continue
            value = _clean(threshold.get("value1") if threshold.get("value1") is not None else threshold.get("value"))
            thresholds.append({"id": None, "key": key, "value": value, "sortOrder": index})
        if thresholds:
            sections["thresholds"] = _format_thresholds(thresholds)

    return sections


def _format_thresholds(thresholds: list[dict[str, Any]]) -> str:
    if not thresholds:
        return "[]"
    lines = ["["]
    for index, threshold in enumerate(thresholds):
        if index:
            lines.append(",")
        raw_id = threshold.get("id")
        id_text = "null" if raw_id in (None, "") else str(raw_id)
        key = str(threshold.get("key", "")).replace("\\", "\\\\").replace('"', '\\"')
        value = str(threshold.get("value", "")).replace("\\", "\\\\").replace('"', '\\"')
        prefix = "    " if index == 0 else ""
        lines.append(f'{prefix}{{id: {id_text}, key: "{key}", value: "{value}", sortOrder: {index}}}')
    lines.append("]")
    return "\n".join(lines)


def _parse_legacy_thresholds(text: str) -> list[dict[str, Any]]:
    thresholds: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^-\s*`(?P<key>[^`]+)`\s*:\s*(?P<value>.+)$", stripped)
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
                "sortOrder": len(thresholds),
            }
        )
    return thresholds


def _apply_missing_sections(target: dict[str, str], fallback: dict[str, str]) -> None:
    for field in SECTION_FIELDS:
        if _field_has_value(field, target.get(field, "")):
            continue
        value = _clean(fallback.get(field, ""))
        if value:
            target[field] = value


def _derive_missing_sections(md_path: str | Path, sections: dict[str, str]) -> None:
    if not _clean(sections.get("inspection_name", "")):
        code = _clean(sections.get("inspection_code", ""))
        if code:
            sections["inspection_name"] = code
        else:
            sections["inspection_name"] = Path(md_path).stem.replace("_", " ")

    if not _clean(sections.get("inspection_content", "")):
        sections["inspection_content"] = _clean(sections.get("inspection_name", ""))

    if not _clean(sections.get("description", "")):
        sections["description"] = _clean(sections.get("inspection_content", ""))

    if not _clean(sections.get("is_required", "")):
        sections["is_required"] = "필수"


def _augment_missing_sections(md_path: str | Path, sections: dict[str, str]) -> dict[str, str]:
    augmented = dict(sections)

    raw_path = _matching_raw_data_path(md_path)
    if raw_path is not None:
        _apply_missing_sections(augmented, _parse_fallback_sections(raw_path.read_text(encoding="utf-8-sig")))

    case_json_path = _matching_case_json_path(md_path)
    if case_json_path is not None:
        _apply_missing_sections(augmented, _fallback_sections_from_case_json(case_json_path))

    thresholds_text = _clean(augmented.get("thresholds", ""))
    if thresholds_text and not _parse_thresholds(thresholds_text):
        legacy_thresholds = _parse_legacy_thresholds(thresholds_text)
        if legacy_thresholds:
            augmented["thresholds"] = _format_thresholds(legacy_thresholds)

    _derive_missing_sections(md_path, augmented)
    return augmented


def _application_lookup_candidates(parsed: dict[str, Any], md_path: str | Path) -> list[str]:
    candidates = [_clean(parsed.get("application", ""))]
    rel_path = _relative_api_data_os_path(Path(md_path))
    if rel_path is not None and len(rel_path.parts) >= 3:
        area_name, application_type, application = rel_path.parts[:3]
        if (
            _normalize_key(area_name) in PRODUCT_APPLICATION_AREAS
            and _normalize_key(application) in PLATFORM_APPLICATION_NAMES
        ):
            candidates.extend(APPLICATION_NAME_ALIASES.get(_normalize_key(application_type), (application_type,)))

    return _dedupe(candidates)


def _existing_item_keys_for_parsed(parsed: dict[str, Any], md_path: str | Path) -> list[tuple[str, str]]:
    code = parsed.get("inspection_code")
    return [_existing_item_key(code, application) for application in _application_lookup_candidates(parsed, md_path)]


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
    sections = _augment_missing_sections(md_path, _parse_sections(text))

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

    def _post_form(self, path: str, form_data: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}{path}",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(f"POST {path} HTTP {response.status_code}: {_compact_response(response)}") from exc
        data = response.json()
        if data.get("status") != "success":
            raise RuntimeError(f"POST {path} API 실패: {data}")
        return data

    def search_existing_items(self, *, batch_size: int = 1000, search_data: str = "") -> list[dict[str, Any]]:
        all_items: list[dict[str, Any]] = []
        seen_ids: set[Any] = set()
        start = 0

        while True:
            end = start + batch_size
            data = self._post_form(
                "/data/inspection/items/search",
                {
                    "selectStartRowNum": str(start),
                    "selectEndRowNum": str(end),
                    "searchTarget": SEARCH_TARGET,
                    "sortData": "[]",
                    "search_data": search_data,
                    "search_target": SEARCH_TARGET,
                    "search_sort_column": "[]",
                },
            ).get("data") or {}
            items = data.get("items") or []
            for item in items:
                item_id = item.get("id")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                all_items.append(item)

            total = int(data.get("total") or len(all_items))
            current_size = int(data.get("current_size") or len(items))
            if len(all_items) >= total or current_size == 0 or len(items) < batch_size:
                break
            start += batch_size

        return all_items

    def seed_management_values_from_md(self, md_path: str | Path) -> None:
        args = ["--md-file", str(md_path), "--quiet"]
        try:
            session_config = InspectionLookupClient._load_session_config(md_path)
        except Exception:
            session_config = {}

        context_path = session_config.get("context_path")
        if context_path:
            args.extend(["--context-file", str(context_path)])

        print(f"[SEED] 관리 값 확인/등록: {md_path}", flush=True)
        try:
            exit_code = seed_inspection_values_main(args)
        except Exception as exc:
            raise InspectionMetadataSeedError(f"{md_path} 관리 값 자동 등록 실패: {exc}") from exc
        if exit_code != 0:
            raise InspectionMetadataSeedError(
                f"{md_path} 관리 값 자동 등록 실패: seed_inspection_values.py exit={exit_code}"
            )

    def resolve_ids_from_parsed(
        self,
        parsed: dict[str, Any],
        md_path: str | Path,
        *,
        seed_missing_metadata: bool,
    ) -> dict[str, Any]:
        candidates = _application_lookup_candidates(parsed, md_path)
        last_error: ValueError | None = None

        for application in candidates:
            try:
                resolved = self.lookup.resolve_ids(
                    inspection_type=parsed["inspection_type"],
                    area=parsed["area"],
                    category=parsed["category"],
                    application_type=parsed["application_type"],
                    application=application,
                )
                if _normalize_key(application) != _normalize_key(parsed["application"]):
                    print(
                        f"[LOOKUP] application 보정: {parsed['application']} -> {resolved['application_name']}",
                        flush=True,
                    )
                return resolved
            except ValueError as exc:
                last_error = exc

        if not seed_missing_metadata:
            if last_error is not None:
                raise last_error
            raise ValueError("application 후보를 만들지 못했습니다.")

        self.seed_management_values_from_md(md_path)
        for application in candidates:
            try:
                return self.lookup.resolve_ids(
                    inspection_type=parsed["inspection_type"],
                    area=parsed["area"],
                    category=parsed["category"],
                    application_type=parsed["application_type"],
                    application=application,
                )
            except ValueError as exc:
                last_error = exc

        if last_error is not None:
            raise last_error
        raise ValueError("application 후보를 만들지 못했습니다.")

    def build_payload_from_md(
        self,
        md_path: str | Path,
        *,
        application_family_id: int | None = None,
        application_version_id: int | None = None,
        is_fix: bool = False,
        seed_missing_metadata: bool = False,
    ) -> dict[str, Any]:
        parsed = parse_api_data_md(md_path)
        resolved = self.resolve_ids_from_parsed(
            parsed,
            md_path,
            seed_missing_metadata=seed_missing_metadata,
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
        seed_missing_metadata: bool = False,
    ) -> dict[str, Any]:
        client, _ = cls.from_api_data_md(md_path)
        return client.build_payload_from_md(
            md_path,
            application_family_id=application_family_id,
            application_version_id=application_version_id,
            is_fix=is_fix,
            seed_missing_metadata=seed_missing_metadata,
        )

    def create_from_md(
        self,
        md_path: str | Path,
        *,
        application_family_id: int | None = None,
        application_version_id: int | None = None,
        is_fix: bool = False,
        seed_missing_metadata: bool = True,
    ) -> dict[str, Any]:
        payload = self.build_payload_from_md(
            md_path,
            application_family_id=application_family_id,
            application_version_id=application_version_id,
            is_fix=is_fix,
            seed_missing_metadata=seed_missing_metadata,
        )
        return self._post("/data/inspection/items", payload)


def _iter_md_paths(md_file: str | None, md_dir: str | None, *, recursive: bool) -> list[Path]:
    if md_file:
        return [Path(md_file).resolve()]
    if not md_dir:
        raise ValueError("--md-file 또는 --md-dir 중 하나를 지정해야 합니다.")

    base_dir = Path(md_dir).resolve()
    paths = base_dir.rglob("*.md") if recursive else base_dir.glob("*.md")
    excluded_parts = {"_logs", "_reports", "_reference", "참고"}
    return sorted(
        path
        for path in paths
        if not any(part in excluded_parts for part in path.relative_to(base_dir).parts)
    )


def _default_log_dir(args: argparse.Namespace) -> Path:
    if getattr(args, "md_dir", None):
        return Path(args.md_dir).resolve() / "_logs"
    if getattr(args, "md_file", None):
        return Path(args.md_file).resolve().parent / "_logs"
    return Path.cwd() / "_logs"


def _build_log_path(args: argparse.Namespace) -> Path | None:
    if getattr(args, "no_log", False):
        return None

    log_dir_value = getattr(args, "log_dir", None)
    log_dir = Path(log_dir_value).resolve() if log_dir_value else _default_log_dir(args)
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S")
    return log_dir / f"inspection_create_{timestamp}.log"


def _write_run_report(
    log_path: Path | None,
    summary: dict[str, Any],
    failed_items: list[dict[str, Any]],
) -> None:
    if log_path is None:
        return

    report_path = log_path.with_suffix(".json")
    report_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "failed_items": failed_items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[LOG_JSON] {report_path}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create inspection items from api_data/os Markdown files.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--md-file", help="Single api_data/os Markdown file to register.")
    target.add_argument("--md-dir", help="Directory containing api_data/os Markdown files.")
    parser.add_argument("--recursive", action="store_true", help="Read Markdown files recursively below --md-dir.")
    parser.add_argument("--execute", action="store_true", help="Send POST requests. Without this, only preview payloads.")
    parser.add_argument("--code", action="append", help="Limit to one inspection_code. Can be repeated.")
    parser.add_argument("--log-dir", help="Directory for per-run logs. Default: <md-dir-or-md-file-parent>/_logs.")
    parser.add_argument("--no-log", action="store_true", help="Do not write the per-run log file.")
    parser.add_argument(
        "--no-seed-missing-metadata",
        action="store_true",
        help="Do not auto-register missing type/area/category/application values before --execute POST.",
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first file error.")
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="POST even when inspection_code + application already exists on the server.",
    )
    return parser.parse_args()


def _run(args: argparse.Namespace, *, log_path: Path | None = None) -> int:
    codes = set(args.code or [])
    try:
        md_paths = _iter_md_paths(args.md_file, args.md_dir, recursive=args.recursive)
        if not md_paths:
            raise ValueError("처리할 Markdown 파일이 없습니다.")
    except Exception as exc:
        print(f"[FAILED] {type(exc).__name__}: {exc}")
        _write_run_report(
            log_path,
            {
                "total": 0,
                "selected": 0,
                "created_or_ready": 0,
                "skipped_existing": 0,
                "skipped_by_code": 0,
                "failed": 1,
            },
            [{"path": args.md_file or args.md_dir, "code": None, "error_type": type(exc).__name__, "error": str(exc)}],
        )
        return 1

    created_or_ready = 0
    skipped_by_code = 0
    skipped_existing = 0
    selected = 0
    failed_items: list[dict[str, Any]] = []
    existing_items_by_key: dict[tuple[str, str], dict[str, Any]] | None = None

    def existing_index(client: InspectionCreateClient) -> dict[tuple[str, str], dict[str, Any]]:
        nonlocal existing_items_by_key
        if existing_items_by_key is None:
            print("[SEARCH] 기존 서버 항목 조회", flush=True)
            existing_items_by_key = {
                _existing_item_key(item.get("inspection_code"), item.get("application_name")): item
                for item in client.search_existing_items()
                if item.get("inspection_code") and item.get("application_name")
            }
        return existing_items_by_key

    for md_path in md_paths:
        parsed: dict[str, Any] | None = None
        inspection_code: str | None = None
        try:
            parsed = parse_api_data_md(md_path)
            inspection_code = parsed["inspection_code"]
            if codes and inspection_code not in codes:
                skipped_by_code += 1
                continue

            selected += 1
            client, _ = InspectionCreateClient.from_api_data_md(md_path)
            if args.execute and not getattr(args, "no_skip_existing", False):
                existing_candidates = [
                    existing_index(client).get(key)
                    for key in _existing_item_keys_for_parsed(parsed, md_path)
                ]
                existing = next((item for item in existing_candidates if item), None)
                if existing:
                    skipped_existing += 1
                    print(
                        f"[SKIP] {inspection_code} {md_path} 이미 등록됨 "
                        f"id={existing.get('id')} item_id={existing.get('item_id')} "
                        f"mapping_id={existing.get('mapping_id')}",
                        flush=True,
                    )
                    continue

            print(f"[LOOKUP] {inspection_code} {md_path}", flush=True)
            seed_missing_metadata = args.execute and not getattr(args, "no_seed_missing_metadata", False)
            payload = client.build_payload_from_md(md_path, seed_missing_metadata=seed_missing_metadata)
            print(f"[POST] {inspection_code} {md_path} execute={args.execute}")
            if not args.execute:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                created_or_ready += 1
                continue

            result = client._post("/data/inspection/items", payload)
            print(f"[RESULT] {inspection_code}: {json.dumps(result, ensure_ascii=False)}")
            if result.get("status") != "success":
                raise RuntimeError(f"{inspection_code} POST 응답 실패: {result}")
            if existing_items_by_key is not None:
                application_name = payload.get("application_name") or parsed.get("application")
                existing_items_by_key[_existing_item_key(inspection_code, application_name)] = {
                    "inspection_code": inspection_code,
                    "application_name": application_name,
                }
            created_or_ready += 1
        except Exception as exc:
            failed_items.append(
                {
                    "path": str(md_path),
                    "code": inspection_code,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            label = inspection_code or md_path.name
            print(f"[ERROR] {label} {md_path}: {type(exc).__name__}: {exc}", flush=True)
            if getattr(args, "fail_fast", False):
                break

    summary = {
        "total": len(md_paths),
        "selected": selected,
        "created_or_ready": created_or_ready,
        "skipped_existing": skipped_existing,
        "skipped_by_code": skipped_by_code,
        "failed": len(failed_items),
    }
    print(f"[SUMMARY] {json.dumps(summary, ensure_ascii=False)}")
    _write_run_report(log_path, summary, failed_items)
    if failed_items:
        print(f"[FAILED_ITEMS] {json.dumps(failed_items, ensure_ascii=False)}")
        return 1
    return 0


def main() -> int:
    args = parse_args()
    log_path = _build_log_path(args)
    if log_path is None:
        return _run(args)

    with log_path.open("w", encoding="utf-8") as log_file:
        with redirect_stdout(_Tee(sys.stdout, log_file)), redirect_stderr(_Tee(sys.stderr, log_file)):
            print(f"[LOG] {log_path}", flush=True)
            return _run(args, log_path=log_path)


if __name__ == "__main__":
    raise SystemExit(main())
