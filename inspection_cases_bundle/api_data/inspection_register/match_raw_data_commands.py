#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Match existing API inspection items to canonical raw Markdown and script.py files.

This helper is not part of the create/update registration flow. It consumes the
/data/inspection/items list response and connects each server row to the local
raw_data/<category>/<application_type>/<application>/<case>.md source plus the
script.py resolved with the same case-directory strategy used by
generate_os_md_from_cases.py.
"""

import contextlib
import io
import json
import re
from pathlib import Path

try:
    from . import fetch_inspection_details as api
    from . import generate_os_md_from_cases
except ImportError:
    import fetch_inspection_details as api
    import generate_os_md_from_cases


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = ROOT_DIR / "raw_data"
DEFAULT_CASE_ROOT = ROOT_DIR / "inspection_cases"
OUTPUT_PATH = ROOT_DIR / "raw_data_command_matches.json"

CATEGORY_ALIASES = {
    "커널": "KERNEL",
    "KERNEL": "KERNEL",
    "KERNAL": "KERNEL",
    "로그": "LOG",
    "LOG": "LOG",
    "NETWORK": "NETWORK",
    "NW": "NETWORK",
    "DISK": "DISK",
    "MEMORY": "MEMORY",
    "CPU": "CPU",
    "OS": "OS",
    "CLUSTER": "CLUSTER",
}


def normalize_category(value):
    text = str(value or "").strip()
    upper = re.sub(r"\s+", " ", text).upper()
    return CATEGORY_ALIASES.get(text, CATEGORY_ALIASES.get(upper, upper))


def strip_code_fence(text):
    value = str(text or "").strip()
    value = re.sub(r"^```[A-Za-z0-9_-]*\s*\n", "", value)
    value = re.sub(r"\n```\s*$", "", value)
    return value.strip()


def normalize_command(value):
    text = strip_code_fence(value)
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = line.strip().strip("`")
        if not line:
            continue
        line = re.sub(r"^[#$]\s+", "", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"(?<!\w)/(?:usr/)?(?:sbin|bin)/", "", text)
    text = re.sub(r"\s*([|;&<>])\s*", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip().lower()


def extract_hash_section(text, section_name):
    pattern = re.compile(r"^#\s+" + re.escape(section_name) + r"\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_match = re.search(r"^#\s+.+?\s*$", text[match.end():], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return strip_code_fence(text[match.end():end])


def extract_bold_field(text, label_names):
    labels = "|".join(re.escape(label) for label in label_names)
    pattern = re.compile(
        rf"^[ \t]*-[ \t]*\*\*(?:{labels})(?:\([^)]*\))?\*\*[ \t]*:[ \t]*(?P<value>.*)$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    inline_value = match.group("value").strip()
    if inline_value:
        return strip_code_fence(inline_value)
    tail = text[match.end():]
    fence = re.search(r"```[A-Za-z0-9_-]*\s*\n(?P<value>.*?)\n```", tail, re.DOTALL)
    if fence:
        return strip_code_fence(fence.group("value"))
    next_field = re.search(r"^[ \t]*-[ \t]*\*\*.+?\*\*[ \t]*:", tail, re.MULTILINE)
    end = next_field.start() if next_field else len(tail)
    return strip_code_fence(tail[:end])


def parse_raw_data(path, raw_root=DEFAULT_RAW_ROOT, case_root=DEFAULT_CASE_ROOT):
    path = Path(path)
    raw_root = Path(raw_root)
    case_root = Path(case_root)
    text = path.read_text(encoding="utf-8")
    area = extract_hash_section(text, "영역") or extract_bold_field(text, ["영역", "area"])
    name = (
        extract_hash_section(text, "세부 점검항목")
        or extract_bold_field(text, ["세부 점검항목", "점검 항목", "inspection item"])
    )
    command = extract_hash_section(text, "명령어") or extract_bold_field(text, ["명령어", "command"])

    try:
        rel_path = path.relative_to(raw_root)
    except ValueError:
        rel_path = Path(path.name)

    case_dir, match_strategy, tried_scripts = generate_os_md_from_cases.resolve_case_dir(
        case_root,
        rel_path,
    )
    script_path = case_dir / "script.py" if case_dir is not None else None

    return {
        "path": str(path),
        "raw_data_path": str(path),
        "relative_path": rel_path.as_posix(),
        "case_name": path.stem,
        "area": area.strip(),
        "normalized_area": normalize_category(area),
        "raw_item_name": name.strip(),
        "raw_command": command.strip(),
        "normalized_command": normalize_command(command),
        "script_path": str(script_path) if script_path is not None else "",
        "script_exists": bool(script_path and script_path.exists()),
        "match_strategy": match_strategy,
        "expected_script": ", ".join(str(item) for item in tried_scripts),
    }


def application_path_variants(application_name):
    value = str(application_name or "").strip().lower()
    variants = {value}
    variants.add(value.replace(" ", "_"))
    variants.add(value.replace(" ", "-"))
    variants.add(re.sub(r"[^a-z0-9]+", "", value))
    variants.add(re.sub(r"[^a-z0-9]+", "_", value).strip("_"))
    variants.add(re.sub(r"[^a-z0-9]+", "-", value).strip("-"))
    return {variant for variant in variants if variant}


def iter_raw_data_files(application_name=None, raw_root=DEFAULT_RAW_ROOT):
    raw_root = Path(raw_root)
    variants = application_path_variants(application_name)
    for path in sorted(raw_root.rglob("*.md")):
        if path.name == "AGENTS.md" or "참고" in path.parts:
            continue
        try:
            rel_path = path.relative_to(raw_root)
        except ValueError:
            continue
        if len(rel_path.parts) != 4:
            continue
        if not variants:
            yield path
            continue
        application_part = rel_path.parts[2]
        if application_path_variants(application_part).intersection(variants):
            yield path


def api_items():
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        response = api.get_inspection_items()
    return response["data"]["items"], response["data"]


def is_ver2_item(item):
    text = " ".join(
        str(item.get(key) or "")
        for key in ("inspection_name", "inspection_code", "code")
    ).lower()
    return "ver2" in text or "버전 2" in text or "version 2" in text


def command_matches(api_command, raw_command):
    api_text = normalize_command(api_command)
    raw_text = normalize_command(raw_command)
    if not api_text or not raw_text:
        return False
    if api_text == raw_text:
        return True

    api_lines = [line for line in api_text.splitlines() if line]
    raw_lines = [line for line in raw_text.splitlines() if line]
    if not api_lines or not raw_lines:
        return False

    for api_line in api_lines:
        if not any(
            raw_line == api_line
            or raw_line.startswith(api_line + " ")
            or api_line.startswith(raw_line + " ")
            for raw_line in raw_lines
        ):
            return False
    return True


def choose_candidate(candidates, item):
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    if is_ver2_item(item):
        for candidate in candidates:
            text = " ".join([
                candidate.get("case_name", ""),
                candidate.get("raw_item_name", ""),
                candidate.get("path", ""),
            ]).lower()
            if "ver2" in text or "버전 2" in text or "version 2" in text:
                return candidate

    item_name = str(item.get("inspection_name") or "").strip().lower()
    for candidate in candidates:
        raw_name = str(candidate.get("raw_item_name") or "").strip().lower()
        if raw_name and (raw_name in item_name or item_name in raw_name):
            return candidate

    return candidates[0]


def choose_match_for_raw_path(matches):
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    for match in matches:
        if is_ver2_item(match):
            return match
    return matches[0]


def build_matches(raw_root=DEFAULT_RAW_ROOT, case_root=DEFAULT_CASE_ROOT):
    items, meta = api_items()
    raws = [
        parse_raw_data(path, raw_root=raw_root, case_root=case_root)
        for path in iter_raw_data_files(api.SESSION["application_name"], raw_root=raw_root)
    ]
    raw_by_key = {}
    for raw in raws:
        if not raw["normalized_command"]:
            continue
        key = (raw["normalized_command"], raw["normalized_area"])
        raw_by_key.setdefault(key, []).append(raw)

    candidate_matches = []
    unmatched_api = []
    for item in items:
        command = normalize_command(item.get("inspection_command"))
        category = normalize_category(item.get("category_name"))
        candidates = raw_by_key.get((command, category), [])
        if not candidates:
            candidates = [
                raw for raw in raws
                if raw["normalized_area"] == category
                and command_matches(item.get("inspection_command"), raw.get("raw_command"))
            ]
        chosen = choose_candidate(candidates, item)
        record = {
            "item_id": item.get("item_id"),
            "mapping_id": item.get("mapping_id"),
            "inspection_code": item.get("inspection_code"),
            "inspection_name": item.get("inspection_name"),
            "category_name": item.get("category_name"),
            "application_name": item.get("application_name"),
            "inspection_command": item.get("inspection_command"),
            "normalized_category": category,
            "normalized_command": command,
            "match_count": len(candidates),
        }
        if chosen:
            candidate_matches.append({
                **record,
                "raw_data_path": chosen["path"],
                "script_path": chosen.get("script_path", ""),
                "script_exists": chosen.get("script_exists", False),
                "match_strategy": chosen.get("match_strategy", ""),
                "expected_script": chosen.get("expected_script", ""),
                "raw_area": chosen["area"],
                "raw_item_name": chosen["raw_item_name"],
                "raw_command": chosen["raw_command"],
                "all_candidate_paths": [candidate["path"] for candidate in candidates],
            })
        else:
            unmatched_api.append(record)

    matches_by_raw_path = {}
    for match in candidate_matches:
        matches_by_raw_path.setdefault(match["raw_data_path"], []).append(match)

    matches = []
    duplicate_api = []
    for _, raw_matches in matches_by_raw_path.items():
        chosen = choose_match_for_raw_path(raw_matches)
        matches.append(chosen)
        duplicate_api.extend(match for match in raw_matches if match is not chosen)

    matches.sort(key=lambda item: (str(item.get("raw_data_path")), str(item.get("inspection_code"))))

    matched_raw_paths = {match["raw_data_path"] for match in matches}
    unmatched_raw = [raw for raw in raws if raw["path"] not in matched_raw_paths]

    return {
        "session": {
            "host": api.HOST,
            "application_name": api.SESSION["application_name"],
            "type_name": api.SESSION["type_name"],
        },
        "api_total": meta.get("total"),
        "api_count": len(items),
        "raw_count": len(raws),
        "candidate_matched_count": len(candidate_matches),
        "matched_count": len(matches),
        "duplicate_api_count": len(duplicate_api),
        "unmatched_api_count": len(unmatched_api),
        "unmatched_raw_count": len(unmatched_raw),
        "matches": matches,
        "duplicate_api": duplicate_api,
        "unmatched_api": unmatched_api,
        "unmatched_raw": unmatched_raw,
    }


def main():
    result = build_matches()
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "summary:",
        json.dumps(
            {
                "application_name": result["session"]["application_name"],
                "type_name": result["session"]["type_name"],
                "api_count": result["api_count"],
                "raw_count": result["raw_count"],
                "candidate_matched_count": result["candidate_matched_count"],
                "matched_count": result["matched_count"],
                "duplicate_api_count": result["duplicate_api_count"],
                "unmatched_api_count": result["unmatched_api_count"],
                "unmatched_raw_count": result["unmatched_raw_count"],
                "output": str(OUTPUT_PATH),
            },
            ensure_ascii=False,
        ),
    )
    print("\nfirst_matches:")
    for item in result["matches"][:10]:
        print(
            f"- {item['inspection_code']} | {item['inspection_name']} | "
            f"{item['inspection_command']} -> {item['raw_data_path']} | "
            f"script={item.get('script_path', '')} | strategy={item.get('match_strategy', '')}"
        )
    if result["unmatched_api"]:
        print("\nunmatched_api:")
        for item in result["unmatched_api"]:
            print(
                f"- {item['inspection_code']} | {item['inspection_name']} | "
                f"{item['category_name']} | {item['inspection_command']}"
            )
    if result["duplicate_api"]:
        print("\nduplicate_api_skipped:")
        for item in result["duplicate_api"]:
            print(
                f"- {item['inspection_code']} | {item['inspection_name']} | "
                f"{item['category_name']} | {item['inspection_command']} -> {item['raw_data_path']}"
            )
    if result["unmatched_raw"]:
        print("\nunmatched_raw:")
        for item in result["unmatched_raw"]:
            print(
                f"- {item['path']} | {item['area']} | {item['raw_item_name']} | "
                f"{item['raw_command']}"
            )


if __name__ == "__main__":
    main()
