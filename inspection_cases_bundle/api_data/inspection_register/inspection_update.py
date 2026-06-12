from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import requests

from inspection_create import InspectionCreateClient, parse_api_data_md
from inspection_lookup import InspectionLookupClient


SEARCH_TARGET = (
    "inspection_code,cve_id,type_name,area_name,category_name,"
    "application_type_name,application_name,application_family_name,"
    "application_version_name,is_required,inspection_name,inspection_content,modified_at"
)


class InspectionUpdateError(RuntimeError):
    pass


def _code_sort_key(code: str) -> tuple[int, int, str]:
    match = re.match(r"^SVR-(\d+)-(\d+)$", str(code or "").strip())
    if not match:
        return (999, 999, str(code or ""))
    return (int(match.group(1)), int(match.group(2)), str(code or ""))


def _normalize_name(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_importance(value: Any) -> Any:
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def _compact_response(response: requests.Response) -> str:
    text = response.text or ""
    return text[:4000]


class InspectionUpdateClient:
    def __init__(self, md_dir: str | Path, *, batch_size: int = 1000, recursive: bool = False):
        self.md_dir = Path(md_dir).resolve()
        self.batch_size = batch_size
        self.recursive = recursive
        self.md_records = self._load_md_records()
        if not self.md_records:
            raise InspectionUpdateError(f"수정할 md 파일이 없습니다: {self.md_dir}")

        first_md = self.md_records[0]["path"]
        self.lookup_client, _ = InspectionLookupClient.from_api_data_md(first_md)
        self.create_client, _ = InspectionCreateClient.from_api_data_md(first_md)

    @classmethod
    def from_os(cls, os_name: str, *, batch_size: int = 1000, recursive: bool = False) -> "InspectionUpdateClient":
        base_dir = Path(__file__).resolve().parents[1]
        return cls(base_dir / "os" / os_name, batch_size=batch_size, recursive=recursive)

    def _iter_md_paths(self) -> list[Path]:
        paths = self.md_dir.rglob("*.md") if self.recursive else self.md_dir.glob("*.md")
        excluded_parts = {"_reports", "_reference", "참고"}
        return sorted(
            path
            for path in paths
            if not any(part in excluded_parts for part in path.relative_to(self.md_dir).parts)
        )

    def _load_md_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in self._iter_md_paths():
            parsed = parse_api_data_md(path)
            records.append(
                {
                    "path": path,
                    "code": parsed["inspection_code"],
                    "application": parsed["application"],
                    "name": parsed["inspection_name"],
                    "parsed": parsed,
                }
            )
        records.sort(key=lambda item: (_normalize_name(item["application"]), _code_sort_key(item["code"])))
        return records

    def _search_page(self, start: int, end: int, search_data: str) -> dict[str, Any]:
        form_data = {
            "selectStartRowNum": str(start),
            "selectEndRowNum": str(end),
            "searchTarget": SEARCH_TARGET,
            "sortData": "[]",
            "search_data": search_data,
            "search_target": SEARCH_TARGET,
            "search_sort_column": "[]",
        }
        response = self.lookup_client.session.post(
            f"{self.lookup_client.base_url}/data/inspection/items/search",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise InspectionUpdateError(f"search API 실패: {payload}")
        return payload.get("data") or {}

    def search_server_items(self, search_data: str) -> list[dict[str, Any]]:
        all_items: list[dict[str, Any]] = []
        seen_ids: set[Any] = set()
        start = 0

        while True:
            end = start + self.batch_size
            data = self._search_page(start, end, search_data)
            items = data.get("items") or []
            for item in items:
                item_id = item.get("id")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                all_items.append(item)

            total = int(data.get("total") or len(all_items))
            current_size = int(data.get("current_size") or len(items))
            if len(all_items) >= total or current_size == 0 or len(items) < self.batch_size:
                break
            start += self.batch_size

        return all_items

    def _find_existing_item(
        self,
        server_items: list[dict[str, Any]],
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        candidates = [
            item
            for item in server_items
            if str(item.get("inspection_code") or "").strip() == record["code"]
            and _normalize_name(item.get("application_name")) == _normalize_name(record["application"])
        ]
        if len(candidates) > 1:
            ids = [item.get("id") for item in candidates]
            raise InspectionUpdateError(f"{record['code']} 항목이 여러 개 매칭됩니다: {ids}")
        return candidates[0] if candidates else None

    def match_records(
        self,
        *,
        search_data: str | None = None,
        codes: set[str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if search_data is None:
            search_data = ""
        server_items = self.search_server_items(search_data)

        matched: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        for record in self.md_records:
            if codes and record["code"] not in codes:
                continue
            existing = self._find_existing_item(server_items, record)
            if existing is None:
                missing.append(record)
                continue
            matched.append({"record": record, "existing": existing})
        return matched, missing

    def create_missing(self, missing: list[dict[str, Any]]) -> None:
        for record in missing:
            path = record["path"]
            print(f"[CREATE] {record['code']} {record['name']} ({path.name})", flush=True)
            result = self.create_client.create_from_md(path)
            print(f"[RESULT] {record['code']}: {json.dumps(result, ensure_ascii=False)}", flush=True)
            if result.get("status") != "success":
                raise InspectionUpdateError(f"{record['code']} create 응답 실패: {result}")

    def build_patch_payload(self, record: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
        payload = self.create_client.build_payload_from_md(record["path"])
        payload.update(
            {
                "id": existing.get("id"),
                "item_id": existing.get("item_id"),
                "mapping_id": existing.get("mapping_id"),
                "cve_id": existing.get("cve_id"),
                "importance": _normalize_importance(existing.get("importance")),
                "application_family_id": existing.get("application_family_id"),
                "application_version_id": existing.get("application_version_id"),
                "is_fix": False,
            }
        )

        required_values = ("id", "item_id", "mapping_id", "type_id", "area_id", "category_id", "application_type_id")
        missing_values = [key for key in required_values if payload.get(key) is None]
        if missing_values:
            raise InspectionUpdateError(f"{record['code']} PATCH payload 필수 값 누락: {missing_values}")
        return payload

    def patch_matched(self, matched: list[dict[str, Any]], *, dry_run: bool) -> int:
        count = 0
        for match in matched:
            record = match["record"]
            existing = match["existing"]
            payload = self.build_patch_payload(record, existing)
            print(
                f"[PATCH] {record['code']} id={payload['id']} item_id={payload['item_id']} "
                f"mapping_id={payload['mapping_id']} name={payload['inspection_name']} dry_run={dry_run}",
                flush=True,
            )
            if dry_run:
                count += 1
                continue

            response = self.create_client.session.patch(
                f"{self.create_client.base_url}/data/inspection/items",
                json=payload,
                timeout=30,
            )
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise InspectionUpdateError(
                    f"{record['code']} PATCH HTTP {response.status_code}: {_compact_response(response)}"
                ) from exc

            result = response.json()
            print(f"[RESULT] {record['code']}: {json.dumps(result, ensure_ascii=False)}", flush=True)
            if result.get("status") != "success":
                raise InspectionUpdateError(f"{record['code']} PATCH 응답 실패: {result}")
            count += 1
        return count

    def update(
        self,
        *,
        execute: bool,
        create_missing: bool,
        search_data: str | None = None,
        codes: set[str] | None = None,
    ) -> dict[str, int]:
        matched, missing = self.match_records(search_data=search_data, codes=codes)
        for match in matched:
            record = match["record"]
            existing = match["existing"]
            print(
                f"[MATCH] {record['code']} id={existing.get('id')} item_id={existing.get('item_id')} "
                f"mapping_id={existing.get('mapping_id')} server_name={existing.get('inspection_name')} "
                f"md_name={record['name']}",
                flush=True,
            )

        if missing:
            for record in missing:
                print(f"[MISSING] {record['code']} {record['name']} ({record['path'].name})", flush=True)
            if not create_missing:
                raise InspectionUpdateError("서버에 없는 항목이 있습니다. 생성하려면 --create-missing 을 사용하세요.")
            if not execute:
                raise InspectionUpdateError("--create-missing 은 실제 생성이 필요하므로 --execute 와 함께 사용하세요.")
            self.create_missing(missing)
            matched, missing = self.match_records(search_data=search_data, codes=codes)
            if missing:
                missing_codes = [record["code"] for record in missing]
                raise InspectionUpdateError(f"생성 후에도 매칭되지 않는 항목이 있습니다: {missing_codes}")

        patched = self.patch_matched(matched, dry_run=not execute)
        return {
            "matched": len(matched),
            "missing": len(missing),
            "patched_or_ready": patched,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update inspection items from api_data/os/<os>/*.md.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--os", dest="os_name", help="OS folder name below api_data/os, e.g. solaris")
    target.add_argument("--md-dir", help="Direct path to an OS md directory")
    parser.add_argument("--execute", action="store_true", help="Send PATCH requests. Without this, only match and preview.")
    parser.add_argument("--create-missing", action="store_true", help="POST-create missing md items before PATCH update.")
    parser.add_argument("--search-data", default="", help="Value for /data/inspection/items/search. Defaults to an empty full search.")
    parser.add_argument("--recursive", action="store_true", help="Read Markdown files recursively below --os/--md-dir.")
    parser.add_argument("--code", action="append", help="Limit to one inspection_code. Can be repeated.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    updater = (
        InspectionUpdateClient.from_os(args.os_name, recursive=args.recursive)
        if args.os_name
        else InspectionUpdateClient(args.md_dir, recursive=args.recursive)
    )
    try:
        summary = updater.update(
            execute=args.execute,
            create_missing=args.create_missing,
            search_data=args.search_data,
            codes=set(args.code or []),
        )
    except Exception as exc:
        print(f"[FAILED] {type(exc).__name__}: {exc}")
        return 1

    print(f"[SUMMARY] {json.dumps(summary, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
