#!/usr/bin/env python3
"""Seed inspection item-management values through the VARS HTTP APIs.

By default this reads the five management values from the NetBackup sample
Markdown and the session information from api_data/api_context.md:

    python3 inspection_cases_bundle/api_data/inspection_register/seed_inspection_values.py

To use another Markdown file:

    python3 inspection_cases_bundle/api_data/inspection_register/seed_inspection_values.py \
        --md-file inspection_cases_bundle/api_data/os/backup/veritas/netbackup_appliance_5240/1_1_catalog.md

The script is idempotent by name where a list API is available: it first looks up
an existing value and only calls the create API when the value is missing.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any, Dict, Iterable, Mapping, Optional

import requests


REPO_ROOT = Path(__file__).resolve().parents[3]
API_DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MD_FILE = (
    "inspection_cases_bundle/api_data/os/backup/veritas/"
    "netbackup_appliance_5240/1_1_catalog.md"
)
DEFAULT_CONTEXT_FILE = "inspection_cases_bundle/api_data/api_context.md"
VALUE_KEYS = ("type_name", "area_name", "category_name", "application_type", "application")
HEADING_PATTERN = re.compile(
    r"^#\s+(?P<title>.+?)\n(?P<body>.*?)(?=^#\s+.+?$|\Z)",
    re.MULTILINE | re.DOTALL,
)
CONTEXT_PATTERN = re.compile(
    r"^##\s+(?P<title>.+?)\n(?P<body>.*?)(?=^##\s+.+?$|\Z)",
    re.MULTILINE | re.DOTALL,
)


# =============================================================================
# 1) 필요하면 이 기본값을 수정하거나 CLI 옵션으로 덮어쓰세요.
# =============================================================================
CONFIG: Dict[str, Any] = {
    # 기본 입력 파일입니다. CLI의 --md-file, --context-file로 덮어쓸 수 있습니다.
    "md_file": DEFAULT_MD_FILE,
    "context_file": DEFAULT_CONTEXT_FILE,

    # 서버 기본 URL입니다. api_context.md의 URL이 있으면 그 값을 우선 사용합니다.
    "base_url": "",

    # 세션값입니다. api_context.md의 SESSION_ID가 있으면 VARS-JSESSIONID로 사용합니다.
    "session": {
        "Language": "ko-KR",
    },
    # 또는 문자열 쿠키를 쓰려면 아래 값을 사용하세요.
    # "cookie_header": "Language=ko-KR; VARS-JSESSIONID=...",

    # md_file을 쓰지 않을 때 넣을 기본값입니다.
    "values": {
        "type_name": "일상점검",
        "area_name": "backup",
        "category_name": "상태점검",
        "application_type": "veritas",
        "application": "netbackup_appliance_5240",
    },

    # 각 유형별 URL입니다. 필요하면 여기서 경로를 바꾸면 됩니다.
    "endpoints": {
        "category_type_list": "/data/inspection/category/types",
        "category_type_create": "/data/inspection/category/types",
        "area_list": "/data/inspection/areas",
        "area_create": "/data/inspection/areas",
        "category_list": "/data/inspection/category/{area_id}",
        "category_create": "/data/inspection/category",
        "application_type_list": "/data/inspection/application/types",
        "application_type_create": "/data/inspection/application/types",
        "application_list": "/data/inspection/applications",
        "application_create": "/data/inspection/applications",
    },

    # 생성 옵션입니다.
    "options": {
        "type_is_vulnerability": True,
        # is_immutable 값을 포함하면 ADMIN 사용자만 성공합니다.
        # 일반 사용자라면 None으로 두세요.
        "type_is_immutable": None,
    },

    # 서버가 느린 환경이라 read timeout은 넉넉하게 둡니다.
    "connect_timeout": 5,
    "request_timeout": 60,
    "verbose": True,
}
# =============================================================================


@dataclass(frozen=True)
class ApiItem:
    id: int
    raw: Mapping[str, Any]


class VarsApiError(RuntimeError):
    pass


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalize_name(value: Any) -> str:
    return clean(value).casefold()


def join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def parse_sections(text: str, pattern: re.Pattern[str]) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    for match in pattern.finditer(text):
        title = clean(match.group("title"))
        body = clean(match.group("body"))
        sections[title] = body
    return sections


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    for base in (Path.cwd(), REPO_ROOT, API_DATA_DIR):
        resolved = base / candidate
        if resolved.exists():
            return resolved
    return REPO_ROOT / candidate


def load_values_from_md(md_file: str | Path) -> Dict[str, str]:
    md_path = resolve_path(md_file)
    sections = parse_sections(md_path.read_text(encoding="utf-8"), HEADING_PATTERN)
    values = {key: clean(sections.get(key, "")) for key in VALUE_KEYS}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise VarsApiError(f"{md_path}에서 {', '.join(missing)} 값을 찾지 못했습니다.")
    return values


def normalize_session_id(value: str) -> str:
    text = clean(value).strip('",')
    match = re.search(r'(?:VARS-)?JSESSIONID=([^;\s,"]+)', text)
    if match:
        return match.group(1)
    return text


def load_context(context_file: str | Path) -> Dict[str, Any]:
    context_path = resolve_path(context_file)
    if not context_path.exists():
        return {}

    sections = parse_sections(context_path.read_text(encoding="utf-8"), CONTEXT_PATTERN)
    session_id = normalize_session_id(
        sections.get("VARS-JSESSIONID", "")
        or sections.get("SESSION_ID", "")
        or sections.get("JSESSIONID", "")
    )
    language = clean(sections.get("language", "")) or "ko-KR"
    result: Dict[str, Any] = {
        "base_url": clean(sections.get("URL", "")),
        "session": {"Language": language},
    }
    if session_id:
        result["session"]["VARS-JSESSIONID"] = session_id
    return result


def cookie_header(config: Mapping[str, Any]) -> str:
    if config.get("cookie_header"):
        return str(config["cookie_header"])
    session = config.get("session") or {}
    return "; ".join(f"{key}={value}" for key, value in session.items() if value)


def unwrap_response(response: requests.Response) -> Any:
    try:
        payload = response.json()
    except ValueError as exc:
        raise VarsApiError(f"JSON 응답이 아닙니다: HTTP {response.status_code} {response.text[:300]}") from exc

    if not response.ok:
        raise VarsApiError(f"HTTP {response.status_code}: {json.dumps(payload, ensure_ascii=False)}")

    if isinstance(payload, dict) and payload.get("status") not in (None, "success"):
        raise VarsApiError(f"API 오류: {json.dumps(payload, ensure_ascii=False)}")

    return payload.get("data") if isinstance(payload, dict) and "data" in payload else payload


def find_by_name(items: Iterable[Mapping[str, Any]], name: str) -> Optional[ApiItem]:
    expected = normalize_name(name)
    for item in items:
        if normalize_name(item.get("name")) == expected:
            item_id = item.get("id")
            if item_id is None:
                continue
            return ApiItem(id=int(item_id), raw=item)
    return None


def extract_items(data: Any, key: str) -> Iterable[Mapping[str, Any]]:
    if not isinstance(data, Mapping):
        return []
    items = data.get(key, [])
    return items if isinstance(items, list) else []


def extract_created_id(data: Any) -> int:
    if isinstance(data, dict):
        for key in ("id", "typeId", "areaId", "categoryId", "applicationTypeId", "applicationId"):
            if data.get(key) is not None:
                return int(data[key])
        for key in ("type", "area", "category", "application", "created", "item"):
            nested = data.get(key)
            if isinstance(nested, dict):
                try:
                    return extract_created_id(nested)
                except VarsApiError:
                    pass
    if isinstance(data, int):
        return data
    if isinstance(data, str) and data.isdigit():
        return int(data)
    raise VarsApiError(f"생성 응답에서 id를 찾을 수 없습니다: {json.dumps(data, ensure_ascii=False)}")


def require_value(values: Mapping[str, Any], key: str) -> str:
    value = clean(values.get(key, ""))
    if not value:
        raise VarsApiError(f"CONFIG['values']['{key}'] 값이 비어 있습니다.")
    return value


class VarsClient:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = config
        self.base_url = str(config["base_url"])
        if not self.base_url:
            raise VarsApiError("base_url 값이 비어 있습니다. api_context.md 또는 --base-url을 확인하세요.")
        self.endpoints = config["endpoints"]
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": cookie_header(config),
            }
        )

    def timeout(self) -> float | tuple[float, float]:
        connect_timeout = self.config.get("connect_timeout")
        request_timeout = float(self.config.get("request_timeout", 60))
        if connect_timeout is None:
            return request_timeout
        return (float(connect_timeout), request_timeout)

    def log_request(self, method: str, path: str, params: Optional[Mapping[str, Any]] = None) -> None:
        if self.config.get("verbose", True):
            suffix = f" params={dict(params)}" if params else ""
            print(f"[{method}] {path}{suffix}")

    def get(
        self,
        endpoint_key: str,
        params: Optional[Mapping[str, Any]] = None,
        **path_params: Any,
    ) -> Any:
        path = self.endpoints[endpoint_key].format(**path_params)
        self.log_request("GET", path, params)
        started = monotonic()
        try:
            response = self.session.get(join_url(self.base_url, path), params=params, timeout=self.timeout())
        except requests.exceptions.RequestException as exc:
            raise VarsApiError(f"GET {path} 요청 실패: {exc}") from exc
        if self.config.get("verbose", True):
            print(f"[GET] {path} -> HTTP {response.status_code} ({monotonic() - started:.2f}s)")
        return unwrap_response(response)

    def post(self, endpoint_key: str, body: Mapping[str, Any]) -> Any:
        path = self.endpoints[endpoint_key]
        self.log_request("POST", path)
        started = monotonic()
        try:
            response = self.session.post(join_url(self.base_url, path), json=body, timeout=self.timeout())
        except requests.exceptions.RequestException as exc:
            raise VarsApiError(f"POST {path} 요청 실패: {exc}") from exc
        if self.config.get("verbose", True):
            print(f"[POST] {path} -> HTTP {response.status_code} ({monotonic() - started:.2f}s)")
        return unwrap_response(response)

    def lookup_category_type(self, name: str) -> Optional[ApiItem]:
        data = self.get("category_type_list") or {}
        return find_by_name(extract_items(data, "types"), name)

    def lookup_area(self, name: str) -> Optional[ApiItem]:
        data = self.get("area_list") or {}
        return find_by_name(extract_items(data, "areas"), name)

    def lookup_category(self, category_type_id: int, area_id: int, name: str) -> Optional[ApiItem]:
        data = self.get("category_list", area_id=area_id, params={"categoryTypeId": category_type_id}) or {}
        return find_by_name(extract_items(data, "categories"), name)

    def lookup_application_type(self, area_id: int, name: str) -> Optional[ApiItem]:
        data = self.get("application_type_list", params={"areaId": area_id}) or {}
        return find_by_name(extract_items(data, "types"), name)

    def lookup_application(self, application_type_id: int, name: str, area_id: Optional[int] = None) -> Optional[ApiItem]:
        params: Dict[str, Any] = {"typeId": application_type_id}
        if area_id is not None:
            params["areaId"] = area_id
        data = self.get("application_list", params=params) or {}
        return find_by_name(extract_items(data, "applications"), name)

    def item_from_create_or_lookup(
        self,
        created: Any,
        lookup: Any,
        label: str,
        name: str,
        raw: Mapping[str, Any],
    ) -> ApiItem:
        try:
            item_id = extract_created_id(created)
            return ApiItem(id=item_id, raw={"id": item_id, "name": name, **raw})
        except VarsApiError:
            found = lookup()
            if found:
                return found
            raise VarsApiError(f"{label} 생성 후 id를 확인하지 못했습니다: {json.dumps(created, ensure_ascii=False)}")

    def ensure_category_type(self, name: str) -> ApiItem:
        found = self.lookup_category_type(name)
        if found:
            print(f"[SKIP] type_name 이미 존재: {name} (id={found.id})")
            return found

        options = self.config.get("options", {})
        body: Dict[str, Any] = {
            "name": name,
            "is_vulnerability": bool(options.get("type_is_vulnerability", True)),
        }
        if options.get("type_is_immutable") is not None:
            body["is_immutable"] = bool(options["type_is_immutable"])

        created = self.post("category_type_create", body)
        item = self.item_from_create_or_lookup(created, lambda: self.lookup_category_type(name), "type_name", name, body)
        print(f"[CREATE] type_name 생성: {name} (id={item.id})")
        return item

    def ensure_area(self, category_type_id: int, name: str) -> ApiItem:
        found = self.lookup_area(name)
        if found:
            print(f"[SKIP] area_name 이미 존재: {name} (id={found.id})")
            return found

        body = {"categoryTypeId": category_type_id, "name": name}
        created = self.post("area_create", body)
        item = self.item_from_create_or_lookup(created, lambda: self.lookup_area(name), "area_name", name, body)
        print(f"[CREATE] area_name 생성/매핑: {name} (id={item.id})")
        return item

    def ensure_category(self, category_type_id: int, area_id: int, name: str) -> ApiItem:
        found = self.lookup_category(category_type_id, area_id, name)
        if found:
            print(f"[SKIP] category_name 이미 존재: {name} (id={found.id})")
            return found

        # InspectionCategory 엔티티는 type_id/area_id를 받습니다. Jackson 호환을 위해
        # camelCase와 snake_case를 함께 보냅니다.
        body = {
            "name": name,
            "typeId": category_type_id,
            "type_id": category_type_id,
            "areaId": area_id,
            "area_id": area_id,
        }
        created = self.post("category_create", body)
        item = self.item_from_create_or_lookup(
            created,
            lambda: self.lookup_category(category_type_id, area_id, name),
            "category_name",
            name,
            body,
        )
        print(f"[CREATE] category_name 생성: {name} (id={item.id})")
        return item

    def ensure_application_type(self, area_id: int, name: str) -> ApiItem:
        found = self.lookup_application_type(area_id, name)
        if found:
            print(f"[SKIP] application_type 이미 존재: {name} (id={found.id})")
            return found

        body = {"areaId": area_id, "area_id": area_id, "name": name}
        created = self.post("application_type_create", body)
        item = self.item_from_create_or_lookup(
            created,
            lambda: self.lookup_application_type(area_id, name),
            "application_type",
            name,
            body,
        )
        print(f"[CREATE] application_type 생성: {name} (id={item.id})")
        return item

    def ensure_application(self, application_type_id: int, area_id: int, name: str) -> ApiItem:
        found = self.lookup_application(application_type_id, name, area_id)
        if found:
            print(f"[SKIP] application 이미 존재: {name} (id={found.id})")
            return found

        body = {
            "application_type_id": application_type_id,
            "applicationTypeId": application_type_id,
            "areaId": area_id,
            "area_id": area_id,
            "name": name,
        }
        created = self.post("application_create", body)
        item = self.item_from_create_or_lookup(
            created,
            lambda: self.lookup_application(application_type_id, name, area_id),
            "application",
            name,
            body,
        )
        print(f"[CREATE] application 생성: {name} (id={item.id})")
        return item


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md-file", default=CONFIG.get("md_file"), help="5개 등록 값을 읽을 Markdown 파일")
    parser.add_argument("--context-file", default=CONFIG.get("context_file"), help="URL/session을 읽을 api_context.md")
    parser.add_argument("--base-url", help="api_context.md 대신 사용할 VARS base URL")
    parser.add_argument("--cookie-header", help="직접 지정할 Cookie header")
    parser.add_argument("--timeout", type=float, help="HTTP read timeout seconds")
    parser.add_argument("--quiet", action="store_true", help="요청 로그를 숨깁니다.")
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> Dict[str, Any]:
    config = copy.deepcopy(CONFIG)

    if args.context_file:
        context = load_context(args.context_file)
        if context.get("base_url"):
            config["base_url"] = context["base_url"]
        if context.get("session"):
            session = dict(config.get("session") or {})
            session.update(context["session"])
            config["session"] = session

    if args.md_file:
        config["values"] = load_values_from_md(args.md_file)
    if args.base_url:
        config["base_url"] = args.base_url
    if args.cookie_header:
        config["cookie_header"] = args.cookie_header
    if args.timeout is not None:
        config["request_timeout"] = args.timeout
    config["verbose"] = not args.quiet
    return config


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    config = build_config(args)
    values = config["values"]
    client = VarsClient(config)

    category_type = client.ensure_category_type(require_value(values, "type_name"))
    area = client.ensure_area(category_type.id, require_value(values, "area_name"))
    category = client.ensure_category(category_type.id, area.id, require_value(values, "category_name"))
    application_type = client.ensure_application_type(area.id, require_value(values, "application_type"))
    application = client.ensure_application(application_type.id, area.id, require_value(values, "application"))

    print("\n완료 결과")
    print(json.dumps(
        {
            "type_name": category_type.raw,
            "area_name": area.raw,
            "category_name": category.raw,
            "application_type": application_type.raw,
            "application": application.raw,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VarsApiError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
    except requests.exceptions.RequestException as exc:
        print(f"[ERROR] HTTP 요청 실패: {exc}", file=sys.stderr)
        raise SystemExit(1)
