from __future__ import annotations

import importlib
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


if __name__ == "__main__":
    unittest.main()
