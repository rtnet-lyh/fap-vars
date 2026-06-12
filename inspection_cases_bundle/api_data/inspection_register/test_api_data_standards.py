from __future__ import annotations

import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


REGISTER_DIR = Path(__file__).resolve().parent
if str(REGISTER_DIR) not in sys.path:
    sys.path.insert(0, str(REGISTER_DIR))


class DummySession:
    def __init__(self):
        self.headers = {}
        self.cookies = {}


requests_stub = types.SimpleNamespace(
    Session=DummySession,
    get=lambda *args, **kwargs: None,
    post=lambda *args, **kwargs: None,
    HTTPError=RuntimeError,
    exceptions=types.SimpleNamespace(RequestException=RuntimeError),
)
sys.modules.setdefault("requests", requests_stub)

inspection_create = importlib.import_module("inspection_create")
inspection_md_parser = importlib.import_module("inspection_md_parser")
fetch_inspection_details = importlib.import_module("fetch_inspection_details")
generate_os_md_from_api_json = importlib.import_module("generate_os_md_from_api_json")
generate_os_md_from_cases = importlib.import_module("generate_os_md_from_cases")


STANDARD_MD = """# type_name

비정기점검

# area_name

보안점검

# category_name

NETWORK

# application_type

UNIX

# application

Solaris

# inspection_code

SVR-7-2

# is_required

필수

# inspection_name

NIC 이중화 점검

# inspection_content

NIC 상태 점검

# inspection_command

```bash
ipmpstat -i
```

# inspection_output

```text
ok
```

# description

설명입니다.

# thresholds

[
    {id: null, key: "min_count", value: "2", sortOrder: 0}
]

# inspection_script

class Check:
    pass
"""


LEGACY_MD = """# 유형

일상점검(상태점검)

# 분야

서버

# 분류

NETWORK

# OS/애플리케이션

UNIX

# 제품명

Solaris

# 코드

SVR-7-2

# 필수

필수

# 점검항목명

NIC 이중화 점검

# 점검 내용

NIC 상태 점검

# 점검명령어

```bash
ipmpstat -i
```

# 출력 값

```text
ok
```

# 설명

설명입니다.

# 기준치

- `min_count`: `2`

# 점검 스크립트

```python
class Check:
    pass
```
"""


class ApiDataStandardsTest(unittest.TestCase):
    def test_parse_api_data_md_uses_standard_english_sections_without_fixed_type_area(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            md_path = Path(tmp_dir) / "case.md"
            md_path.write_text(STANDARD_MD, encoding="utf-8")

            parsed = inspection_create.parse_api_data_md(md_path)

        self.assertEqual(parsed["inspection_type"], "비정기점검")
        self.assertEqual(parsed["area"], "보안점검")
        self.assertEqual(parsed["category"], "NETWORK")
        self.assertEqual(parsed["application_type"], "UNIX")
        self.assertEqual(parsed["application"], "Solaris")
        self.assertEqual(parsed["is_required"], 1)
        self.assertEqual(parsed["inspection_command"], "ipmpstat -i")
        self.assertEqual(parsed["inspection_output"], "ok")
        self.assertEqual(parsed["thresholds"], [{"id": None, "key": "min_count", "value": "2", "sortOrder": 0}])

    def test_legacy_korean_parser_is_explicitly_separate_but_normalizes_to_same_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            md_path = Path(tmp_dir) / "legacy.md"
            md_path.write_text(LEGACY_MD, encoding="utf-8")

            parsed = inspection_md_parser.parse_legacy_inspection_md(md_path)
            alias_parsed = inspection_md_parser.parse_inspection_md(md_path)

        self.assertEqual(parsed, alias_parsed)
        self.assertEqual(parsed["inspection_type"], "일상점검(상태점검)")
        self.assertEqual(parsed["area"], "서버")
        self.assertEqual(parsed["category"], "network")
        self.assertEqual(parsed["thresholds"], [{"id": None, "key": "min_count", "value": "2", "sortOrder": 0}])

    def test_api_context_ignores_item_id_values_and_requires_fetch_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            context_path = Path(tmp_dir) / "api_context.md"
            context_path.write_text(
                """## URL

http://example.test/

## JSESSIONID

JSESSIONID=abc123; Path=/

## language

en-US

## application_name

Solaris

## type_name

정기점검

## item_id

999
""",
                encoding="utf-8",
            )

            config = fetch_inspection_details.load_context_config(context_path)

        self.assertEqual(config["host"], "http://example.test")
        self.assertEqual(config["jsessionid"], "abc123")
        self.assertEqual(config["language"], "en-US")
        self.assertEqual(config["application_name"], "Solaris")
        self.assertEqual(config["type_name"], "정기점검")
        self.assertNotIn("item_id", config)
        self.assertNotIn("item_ids", config)

    def test_generate_os_md_from_api_json_round_trips_with_parse_api_data_md(self) -> None:
        item = {
            "type_name": "정기점검",
            "area_name": "보안점검",
            "category_name": "server",
            "application_name": "Rocky Linux",
            "inspection_code": "LINUX-CPU-001",
            "is_required": "필수",
            "inspection_name": "CPU 사용률",
            "inspection_content": "CPU 사용률 점검",
            "inspection_command": "top -bn1",
            "inspection_output": "Cpu(s): 1.0 us",
            "description": "CPU 사용률을 확인합니다.",
            "inspection_script": "case_name = 'rocky_cpu_check'\nclass Check:\n    pass\n",
            "thresholds": [{"id": None, "key": "max_cpu_usage_percent", "value": "80", "sortOrder": 0}],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "os"
            output_path = generate_os_md_from_api_json.output_path_for_item(
                item,
                output_root,
                application_type="linux",
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                generate_os_md_from_api_json.build_md(item, application_type="linux"),
                encoding="utf-8",
            )

            parsed = inspection_create.parse_api_data_md(output_path)

        self.assertEqual(output_path.relative_to(output_root).as_posix(), "server/linux/Rocky_Linux/rocky_cpu_check.md")
        self.assertEqual(parsed["inspection_type"], "정기점검")
        self.assertEqual(parsed["area"], "보안점검")
        self.assertEqual(parsed["application_type"], "linux")
        self.assertEqual(parsed["application"], "Rocky Linux")
        self.assertEqual(parsed["inspection_code"], "LINUX-CPU-001")
        self.assertEqual(parsed["thresholds"], [{"id": None, "key": "max_cpu_usage_percent", "value": "80", "sortOrder": 0}])

    def test_generate_os_md_from_cases_combines_raw_case_json_and_script_then_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_root = base / "raw_data"
            case_root = base / "inspection_cases"
            output_root = base / "api_data" / "os"
            report_root = base / "api_data" / "_reports"

            raw_path = raw_root / "server" / "linux" / "rocky" / "cpu.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(
                """# 영역

CPU

# 세부 점검항목

CPU 사용률

# 점검 내용

CPU 사용률 점검

# 구분

필수

# 명령어

```bash
top -bn1
```

# 출력 결과

```text
Cpu(s): 1.0 us
```

# 설명

CPU 사용률을 확인합니다.

# 판단기준

임계치 미만이면 양호입니다.
""",
                encoding="utf-8",
            )

            case_dir = case_root / "server" / "linux" / "rocky" / "cpu"
            case_dir.mkdir(parents=True, exist_ok=True)
            (case_dir / "script.py").write_text("class Check:\n    pass\n", encoding="utf-8")
            (case_dir / "case.json").write_text(
                json.dumps(
                    {
                        "item": {
                            "inspection_code": "LINUX-CPU-001",
                            "threshold_list": [
                                {"name": "max_cpu_usage_percent", "value1": "80"},
                            ],
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            summary = generate_os_md_from_cases.convert_all(
                raw_root=raw_root,
                case_root=case_root,
                output_root=output_root,
                report_root=report_root,
                dry_run=False,
                overwrite=False,
                type_name="정기점검",
                area_name="보안점검",
            )
            output_path = output_root / "server" / "linux" / "rocky" / "cpu.md"
            parsed = inspection_create.parse_api_data_md(output_path)

        self.assertEqual(summary.generated_count, 1)
        self.assertEqual(summary.skipped_count, 0)
        self.assertEqual(parsed["inspection_type"], "정기점검")
        self.assertEqual(parsed["area"], "보안점검")
        self.assertEqual(parsed["category"], "server")
        self.assertEqual(parsed["application_type"], "linux")
        self.assertEqual(parsed["application"], "rocky")
        self.assertEqual(parsed["inspection_code"], "LINUX-CPU-001")
        self.assertEqual(parsed["inspection_command"], "top -bn1")
        self.assertEqual(parsed["inspection_output"], "Cpu(s): 1.0 us")
        self.assertIn("임계치 미만", parsed["description"])
        self.assertEqual(parsed["thresholds"], [{"id": None, "key": "max_cpu_usage_percent", "value": "80", "sortOrder": 0}])


if __name__ == "__main__":
    unittest.main()
