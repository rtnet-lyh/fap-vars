#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import html
import io
import json
import re
import shutil
import sys
from pathlib import Path

try:
    from . import fetch_inspection_details as api
    from . import match_raw_data_commands
except ImportError:
    import fetch_inspection_details as api
    import match_raw_data_commands


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = ROOT_DIR / "api_script_sync_validation.json"
BACKUP_ROOT = ROOT_DIR / "api_data" / "inspection_register" / "backups"


def normalize_script_text(value) -> str:
    """Decode common response wrapping and normalize script newlines to LF."""
    if value is None:
        return ""

    text = str(value)
    text = html.unescape(text)

    stripped = text.strip()
    if (
        len(stripped) >= 2
        and stripped[0] == stripped[-1]
        and stripped[0] in {"'", '"'}
    ):
        try:
            decoded = json.loads(stripped)
            if isinstance(decoded, str):
                text = decoded
        except json.JSONDecodeError:
            pass

    actual_newlines = text.count("\n")
    escaped_newlines = len(re.findall(r"\\r\\n|\\n|\\r", text))
    if actual_newlines < 2 and escaped_newlines >= 2:
        try:
            decoded = json.loads(f'"{text}"')
            if isinstance(decoded, str) and decoded.count("\n") > actual_newlines:
                text = decoded
        except json.JSONDecodeError:
            text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_code_fence(text)
    return text.rstrip() + "\n" if text.strip() else ""


def strip_code_fence(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(r"^```[A-Za-z0-9_-]*\s*\n", "", value)
    value = re.sub(r"\n```\s*$", "", value)
    return value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def script_path_for_match(match: dict) -> Path:
    raw_data_path = Path(match["raw_data_path"])
    return raw_data_path.parent / "script.py"


def get_detail_silently(item_id, mapping_id) -> dict:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        return api.get_item_detail(item_id, mapping_id)


def validate_python_source(script_text: str, script_path: Path) -> list[str]:
    errors = []
    if not script_text.strip():
        errors.append("inspection_script is empty")
        return errors

    required_markers = ("class Check", "CHECK_CLASS")
    missing = [marker for marker in required_markers if marker not in script_text]
    if missing:
        errors.append("missing markers: " + ", ".join(missing))

    try:
        compile(script_text, str(script_path), "exec")
    except SyntaxError as exc:
        errors.append(f"syntax error: line {exc.lineno}: {exc.msg}")

    return errors


def build_plan() -> dict:
    match_result = match_raw_data_commands.build_matches()
    detail_by_key = {}
    records = []
    errors = []

    for match in match_result["matches"]:
        key = (match.get("item_id"), match.get("mapping_id"))
        if key not in detail_by_key:
            detail_by_key[key] = get_detail_silently(*key)
        detail = detail_by_key[key]

        script_path = script_path_for_match(match)
        api_script = normalize_script_text(detail.get("inspection_script"))
        old_script = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
        validation_errors = validate_python_source(api_script, script_path)

        record = {
            "item_id": match.get("item_id"),
            "mapping_id": match.get("mapping_id"),
            "inspection_code": match.get("inspection_code"),
            "inspection_name": match.get("inspection_name"),
            "category_name": match.get("category_name"),
            "inspection_command": match.get("inspection_command"),
            "raw_data_path": match.get("raw_data_path"),
            "script_path": str(script_path),
            "script_exists": script_path.exists(),
            "api_script_length": len(api_script),
            "old_script_length": len(old_script),
            "api_script_sha256": sha256_text(api_script) if api_script else "",
            "old_script_sha256": sha256_text(old_script) if old_script else "",
            "changed": api_script != old_script,
            "validation_errors": validation_errors,
        }
        records.append(record)
        errors.extend(
            {
                "script_path": str(script_path),
                "inspection_code": match.get("inspection_code"),
                "error": error,
            }
            for error in validation_errors
        )

    summary = {
        "host": api.HOST,
        "application_name": api.SESSION["application_name"],
        "type_name": api.SESSION["type_name"],
        "api_count": match_result["api_count"],
        "raw_count": match_result["raw_count"],
        "matched_count": match_result["matched_count"],
        "duplicate_api_count": match_result["duplicate_api_count"],
        "unmatched_api_count": match_result["unmatched_api_count"],
        "unmatched_raw_count": match_result["unmatched_raw_count"],
        "records_count": len(records),
        "changed_count": sum(1 for record in records if record["changed"]),
        "unchanged_count": sum(1 for record in records if not record["changed"]),
        "validation_error_count": len(errors),
    }

    return {
        "summary": summary,
        "records": records,
        "validation_errors": errors,
        "duplicate_api": match_result["duplicate_api"],
        "unmatched_api": match_result["unmatched_api"],
        "unmatched_raw": match_result["unmatched_raw"],
        "_details": detail_by_key,
    }


def ensure_safe_to_write(plan: dict, *, allow_partial: bool) -> None:
    summary = plan["summary"]
    problems = []
    if summary["validation_error_count"]:
        problems.append(f"validation_error_count={summary['validation_error_count']}")
    if not allow_partial:
        for key in ("unmatched_api_count", "unmatched_raw_count"):
            if summary[key]:
                problems.append(f"{key}={summary[key]}")

    if problems:
        raise RuntimeError("검증 실패로 갱신을 중단합니다: " + ", ".join(problems))


def backup_existing_scripts(records: list[dict], backup_dir: Path) -> list[dict]:
    backup_dir.mkdir(parents=True, exist_ok=False)
    manifest = []

    for record in records:
        script_path = Path(record["script_path"])
        if not script_path.exists():
            continue
        relative_path = script_path.relative_to(ROOT_DIR)
        backup_path = backup_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(script_path, backup_path)
        manifest.append({
            "script_path": str(script_path),
            "backup_path": str(backup_path),
            "old_script_sha256": record["old_script_sha256"],
        })

    (backup_dir / "backup_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def write_report(plan: dict, report_path: Path) -> None:
    public_plan = {key: value for key, value in plan.items() if not key.startswith("_")}
    report_path.write_text(json.dumps(public_plan, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_updates(plan: dict, backup_dir: Path) -> dict:
    records = plan["records"]
    detail_by_key = plan["_details"]
    backups = backup_existing_scripts(records, backup_dir)

    updated = []
    skipped_unchanged = []
    for record in records:
        script_path = Path(record["script_path"])
        detail = detail_by_key[(record["item_id"], record["mapping_id"])]
        api_script = normalize_script_text(detail.get("inspection_script"))

        if not record["changed"]:
            skipped_unchanged.append(str(script_path))
            continue

        script_path.write_text(api_script, encoding="utf-8", newline="\n")
        updated.append(str(script_path))

    return {
        "backup_dir": str(backup_dir),
        "backup_count": len(backups),
        "updated_count": len(updated),
        "unchanged_count": len(skipped_unchanged),
        "updated": updated,
        "unchanged": skipped_unchanged,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Match raw_data.md files to API items and sync API inspection_script into script.py."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually overwrite matched script.py files. Default only validates and writes the report.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow write when unmatched API/raw entries exist. Validation errors still stop writes.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help=f"Validation report path. Default: {DEFAULT_REPORT_PATH}",
    )
    parser.add_argument(
        "--backup-dir",
        default="",
        help="Backup directory for --write. Default: timestamped directory under api_data/inspection_register/backups.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = ROOT_DIR / report_path

    try:
        plan = build_plan()
        write_report(plan, report_path)

        print("validation_summary:", json.dumps(plan["summary"], ensure_ascii=False))
        print("report:", report_path)
        print("first_targets:")
        for record in plan["records"][:10]:
            print(
                f"- {record['inspection_code']} | {record['inspection_name']} -> "
                f"{record['script_path']} | changed={record['changed']} | "
                f"errors={len(record['validation_errors'])}"
            )

        if not args.write:
            print("mode: dry-run")
            return 0

        ensure_safe_to_write(plan, allow_partial=args.allow_partial)
        if args.backup_dir:
            backup_dir = Path(args.backup_dir)
            if not backup_dir.is_absolute():
                backup_dir = ROOT_DIR / backup_dir
        else:
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = BACKUP_ROOT / f"script_sync_{stamp}"

        result = apply_updates(plan, backup_dir)
        plan["apply_result"] = result
        write_report(plan, report_path)
        print("apply_result:", json.dumps(result, ensure_ascii=False))
        return 0

    except Exception as exc:
        print(f"[FAILED] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
