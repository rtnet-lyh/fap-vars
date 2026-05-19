import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "hpux_inspection_details.json"
OUTPUT_DIR = BASE_DIR.parent / "os" / "hp-ux"
IS_ESSENTIAL_PATH = BASE_DIR.parent / "os" / "solaris" / "참고" / "is_essential.md"

CASE_NAME_RE = re.compile(r"case_name\s*[:=]\s*['\"]([\w_-]+)['\"]")


def normalize_newlines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_")
    if sanitized == "":
        return "item"
    return sanitized


def load_is_required_map() -> dict[str, str]:
    text = IS_ESSENTIAL_PATH.read_text(encoding="utf-8")
    rows = re.findall(r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|", text)
    return {row[1].strip(): row[3].strip() for row in rows}


def extract_case_name(script: str, inspection_code: str, inspection_name: str) -> str:
    match = CASE_NAME_RE.search(script)
    if match:
        return match.group(1)
    code_part = sanitize_filename(str(inspection_code or "").lower())
    name_part = sanitize_filename(inspection_name)
    base_name = "hpux"
    if code_part:
        base_name += f"_{code_part}"
    if name_part:
        base_name += f"_{name_part}"
    if base_name.endswith("_check"):
        return base_name
    return f"{base_name}_check"


def build_md(item: dict[str, str], is_required_value: str) -> str:
    inspection_command = normalize_newlines(item.get("inspection_command") or "").strip()
    inspection_output = normalize_newlines(item.get("inspection_output") or "").strip()
    description = normalize_newlines(item.get("description") or "").strip()
    script = normalize_newlines(item.get("inspection_script") or "").rstrip()

    md = []
    md.append("# type_name\n")
    md.append(item.get("type_name", ""))
    md.append("\n# area_name\n")
    md.append(item.get("area_name", ""))
    md.append("\n# category_name\n")
    md.append(item.get("category_name", ""))
    md.append("\n# application_type\n")
    md.append(item.get("application_type_name", "UNIX") or "UNIX")
    md.append("\n# application\n")
    md.append(item.get("application_name", ""))
    md.append("\n# inspection_code\n")
    md.append(item.get("inspection_code", ""))
    md.append("\n# is_required\n")
    md.append(is_required_value)
    md.append("\n# inspection_name\n")
    md.append(item.get("inspection_name", ""))
    md.append("\n# inspection_content\n")
    md.append(item.get("inspection_content", ""))
    md.append("\n# inspection_command\n")
    md.append("```bash\n" + inspection_command + "\n```" if inspection_command else "```bash\n\n```")
    md.append("\n# inspection_output\n")
    md.append("```text\n" + inspection_output + "\n```" if inspection_output else "```text\n\n```")
    md.append("\n# description\n")
    md.append(description)
    md.append("\n# thresholds\n")
    md.append("[]")
    md.append("\n# inspection_script\n")
    md.append(script)
    return "\n".join(md).strip() + "\n"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    is_required_map = load_is_required_map()

    with open(JSON_PATH, encoding="utf-8") as f:
        items = json.load(f)

    names = {}
    created = []
    for item in items:
        inspection_name = item.get("inspection_name", "")
        mapping_value = is_required_map.get(inspection_name, None)
        is_required_value = mapping_value if mapping_value is not None else "false"
        script = normalize_newlines(item.get("inspection_script") or "")
        case_name = extract_case_name(script, item.get("inspection_code", ""), inspection_name)

        if case_name in names:
            names[case_name] += 1
            case_name = f"{case_name}_{names[case_name]}"
        else:
            names[case_name] = 1

        output_path = OUTPUT_DIR / f"{case_name}.md"
        output_path.write_text(build_md(item, is_required_value), encoding="utf-8")
        created.append(output_path.name)

    print(f"created {len(created)} md files in {OUTPUT_DIR}")
    for name in created:
        print(name)


if __name__ == "__main__":
    main()
