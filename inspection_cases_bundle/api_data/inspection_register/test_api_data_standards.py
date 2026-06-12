from __future__ import annotations

import contextlib
import importlib
import io
import json
import sys
from argparse import Namespace
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
inspection_update = importlib.import_module("inspection_update")
inspection_lookup = importlib.import_module("inspection_lookup")
generate_os_md_from_api_json = importlib.import_module("generate_os_md_from_api_json")
generate_os_md_from_cases = importlib.import_module("generate_os_md_from_cases")
match_raw_data_commands = importlib.import_module("match_raw_data_commands")
sync_scripts_from_api = importlib.import_module("sync_scripts_from_api")


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

    def test_fetch_details_uses_list_row_ids_and_thresholds_only_when_requested(self) -> None:
        original_get_items = fetch_inspection_details.get_inspection_items
        original_get_detail = fetch_inspection_details.get_item_detail
        original_get_thresholds = fetch_inspection_details.get_item_thresholds
        calls: list[tuple[str, object, object | None]] = []

        def fake_get_items() -> dict[str, object]:
            return {
                "data": {
                    "items": [
                        {"item_id": 101, "mapping_id": 501},
                        {"item_id": 102, "mapping_id": 502},
                    ]
                }
            }

        def fake_get_detail(item_id: object, mapping_id: object) -> dict[str, object]:
            calls.append(("detail", item_id, mapping_id))
            return {"item_id": item_id, "mapping_id": mapping_id, "inspection_code": f"CODE-{item_id}"}

        def fake_get_thresholds(item_id: object) -> list[dict[str, object]]:
            calls.append(("thresholds", item_id, None))
            return [{"key": "limit", "value": str(item_id)}]

        try:
            fetch_inspection_details.get_inspection_items = fake_get_items
            fetch_inspection_details.get_item_detail = fake_get_detail
            fetch_inspection_details.get_item_thresholds = fake_get_thresholds

            with contextlib.redirect_stdout(io.StringIO()):
                without_thresholds = fetch_inspection_details.fetch_details(include_thresholds=False)
            self.assertEqual(calls, [("detail", 101, 501), ("detail", 102, 502)])
            self.assertNotIn("thresholds", without_thresholds[0])

            calls.clear()
            with contextlib.redirect_stdout(io.StringIO()):
                with_thresholds = fetch_inspection_details.fetch_details(include_thresholds=True)
            self.assertEqual(
                calls,
                [
                    ("detail", 101, 501),
                    ("thresholds", 101, None),
                    ("detail", 102, 502),
                    ("thresholds", 102, None),
                ],
            )
            self.assertEqual(with_thresholds[0]["thresholds"], [{"key": "limit", "value": "101"}])
        finally:
            fetch_inspection_details.get_inspection_items = original_get_items
            fetch_inspection_details.get_item_detail = original_get_detail
            fetch_inspection_details.get_item_thresholds = original_get_thresholds

    def test_fetch_get_inspection_items_uses_context_filters(self) -> None:
        original_get = fetch_inspection_details.requests.get
        original_session = fetch_inspection_details.SESSION
        original_host = fetch_inspection_details.HOST
        captured: dict[str, object] = {}

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"status": "success", "data": {"items": []}}

        def fake_get(url: str, *, params: dict[str, object], headers: dict[str, str], timeout: int) -> FakeResponse:
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            captured["timeout"] = timeout
            return FakeResponse()

        try:
            fetch_inspection_details.requests.get = fake_get
            fetch_inspection_details.SESSION = {
                "host": "http://api.example.test",
                "language": "ko-KR",
                "jsessionid": "session-id",
                "application_name": "Solaris",
                "type_name": "정기점검",
            }
            fetch_inspection_details.HOST = "http://api.example.test"

            fetch_inspection_details.get_inspection_items()

            filter_data = json.loads(captured["params"]["filterData"])
        finally:
            fetch_inspection_details.requests.get = original_get
            fetch_inspection_details.SESSION = original_session
            fetch_inspection_details.HOST = original_host

        self.assertEqual(captured["url"], "http://api.example.test/data/inspection/items")
        self.assertEqual(captured["timeout"], 30)
        self.assertEqual(
            filter_data,
            [
                {"column": "type_name", "values": ["정기점검"]},
                {"column": "application_name", "values": ["Solaris"]},
            ],
        )

    def test_inspection_lookup_prefers_api_context_and_falls_back_to_legacy_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            api_data = Path(tmp_dir) / "api_data"
            md_path = api_data / "os" / "server" / "linux" / "rocky" / "case.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text("# placeholder\n", encoding="utf-8")
            (api_data / "api_context.md").write_text(
                """## URL

http://context.example/

## SESSION_ID

ctx-session

## language

ko-KR
""",
                encoding="utf-8",
            )
            (api_data / "session.md").write_text(
                """## URL

http://legacy.example/

## SESSION_ID

legacy-session
""",
                encoding="utf-8",
            )

            preferred = inspection_lookup.InspectionLookupClient._load_session_config(md_path)
            (api_data / "api_context.md").unlink()
            fallback = inspection_lookup.InspectionLookupClient._load_session_config(md_path)

        self.assertEqual(preferred["base_url"], "http://context.example")
        self.assertEqual(preferred["jsessionid"], "ctx-session")
        self.assertEqual(fallback["base_url"], "http://legacy.example")
        self.assertEqual(fallback["jsessionid"], "legacy-session")

    def test_inspection_create_main_previews_without_post_when_execute_is_false(self) -> None:
        original_parse_args = inspection_create.parse_args
        original_iter = inspection_create._iter_md_paths
        original_parse_md = inspection_create.parse_api_data_md
        original_from_md = inspection_create.InspectionCreateClient.from_api_data_md
        calls: list[str] = []
        fake_path = Path("/tmp/fake.md")

        class FakeClient:
            def build_payload_from_md(self, md_path: Path) -> dict[str, object]:
                calls.append(f"build:{md_path}")
                return {"inspection_code": "CODE-1"}

            def create_from_md(self, md_path: Path) -> dict[str, object]:
                calls.append(f"create:{md_path}")
                return {"status": "success"}

        try:
            inspection_create.parse_args = lambda: Namespace(
                md_file=None,
                md_dir="unused",
                recursive=False,
                execute=False,
                code=None,
            )
            inspection_create._iter_md_paths = lambda md_file, md_dir, *, recursive: [fake_path]
            inspection_create.parse_api_data_md = lambda md_path: {
                "inspection_code": "CODE-1",
                "inspection_name": "점검",
            }
            inspection_create.InspectionCreateClient.from_api_data_md = classmethod(lambda cls, md_path: (FakeClient(), {}))

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = inspection_create.main()
        finally:
            inspection_create.parse_args = original_parse_args
            inspection_create._iter_md_paths = original_iter
            inspection_create.parse_api_data_md = original_parse_md
            inspection_create.InspectionCreateClient.from_api_data_md = original_from_md

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, ["build:/tmp/fake.md"])

    def test_inspection_update_defaults_to_full_search_and_matches_code_and_application(self) -> None:
        updater = inspection_update.InspectionUpdateClient.__new__(inspection_update.InspectionUpdateClient)
        updater.md_records = [
            {"code": "CODE-1", "application": "Solaris", "name": "match"},
            {"code": "CODE-2", "application": "Solaris", "name": "missing"},
        ]
        captured: dict[str, str] = {}

        def fake_search(search_data: str) -> list[dict[str, object]]:
            captured["search_data"] = search_data
            return [
                {"id": 1, "inspection_code": "CODE-1", "application_name": "Solaris"},
                {"id": 2, "inspection_code": "CODE-2", "application_name": "AIX"},
            ]

        updater.search_server_items = fake_search

        matched, missing = updater.match_records()

        self.assertEqual(captured["search_data"], "")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["existing"]["id"], 1)
        self.assertEqual([record["code"] for record in missing], ["CODE-2"])

    def test_match_raw_data_commands_uses_canonical_raw_and_resolves_script_path(self) -> None:
        original_api_items = match_raw_data_commands.api_items
        original_session = dict(match_raw_data_commands.api.SESSION)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_root = root / "raw_data"
            case_root = root / "inspection_cases"
            raw_path = raw_root / "server" / "linux" / "rocky" / "cpu_usage.md"
            script_path = case_root / "server" / "linux" / "rocky" / "cpu_usage" / "script.py"
            raw_path.parent.mkdir(parents=True)
            script_path.parent.mkdir(parents=True)
            raw_path.write_text(
                "# 영역\n\nCPU\n\n"
                "# 세부 점검항목\n\nCPU 사용률 점검\n\n"
                "# 명령어\n\n```bash\ntop -bn1\n```\n",
                encoding="utf-8",
            )
            script_path.write_text("class Check:\n    pass\n\nCHECK_CLASS = Check\n", encoding="utf-8")

            def fake_api_items() -> tuple[list[dict[str, object]], dict[str, object]]:
                return [
                    {
                        "item_id": 101,
                        "mapping_id": 202,
                        "inspection_code": "LINUX-CPU-001",
                        "inspection_name": "CPU 사용률 점검",
                        "category_name": "CPU",
                        "application_name": "rocky",
                        "inspection_command": "top -bn1",
                    }
                ], {"total": 1}

            try:
                match_raw_data_commands.api_items = fake_api_items
                match_raw_data_commands.api.SESSION.update({"application_name": "rocky", "type_name": "정기점검"})
                result = match_raw_data_commands.build_matches(raw_root=raw_root, case_root=case_root)
            finally:
                match_raw_data_commands.api_items = original_api_items
                match_raw_data_commands.api.SESSION.clear()
                match_raw_data_commands.api.SESSION.update(original_session)

        self.assertEqual(result["matched_count"], 1)
        match = result["matches"][0]
        self.assertEqual(match["raw_data_path"], str(raw_path))
        self.assertEqual(match["script_path"], str(script_path))
        self.assertEqual(match["match_strategy"], "same_parent:exact")
        self.assertEqual(match["item_id"], 101)
        self.assertEqual(match["mapping_id"], 202)

    def test_sync_scripts_uses_match_script_path_and_blocks_validation_errors(self) -> None:
        explicit_script = Path("/tmp/correct/script.py")
        fallback_raw = Path("/tmp/wrong/raw_data.md")
        resolved = sync_scripts_from_api.script_path_for_match({
            "script_path": str(explicit_script),
            "raw_data_path": str(fallback_raw),
        })

        self.assertEqual(resolved, explicit_script)
        with self.assertRaisesRegex(RuntimeError, "validation_error_count=1"):
            sync_scripts_from_api.ensure_safe_to_write(
                {
                    "summary": {
                        "validation_error_count": 1,
                        "unmatched_api_count": 0,
                        "unmatched_raw_count": 0,
                    }
                },
                allow_partial=True,
            )

    def test_sync_apply_updates_writes_backup_manifest(self) -> None:
        original_root = sync_scripts_from_api.ROOT_DIR
        old_script = "class Check:\n    pass\n\nCHECK_CLASS = Check\n"
        new_script = "class Check:\n    value = 1\n\nCHECK_CLASS = Check\n"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script_path = root / "inspection_cases" / "server" / "linux" / "rocky" / "cpu_usage" / "script.py"
            backup_dir = root / "backups" / "sync"
            script_path.parent.mkdir(parents=True)
            script_path.write_text(old_script, encoding="utf-8")
            detail_key = (101, 202)
            plan = {
                "records": [
                    {
                        "item_id": 101,
                        "mapping_id": 202,
                        "script_path": str(script_path),
                        "changed": True,
                        "old_script_sha256": sync_scripts_from_api.sha256_text(old_script),
                    }
                ],
                "_details": {detail_key: {"inspection_script": new_script}},
            }

            try:
                sync_scripts_from_api.ROOT_DIR = root
                result = sync_scripts_from_api.apply_updates(plan, backup_dir)
            finally:
                sync_scripts_from_api.ROOT_DIR = original_root

            manifest_path = backup_dir / "backup_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            backup_path = Path(manifest[0]["backup_path"])

            self.assertEqual(result["backup_count"], 1)
            self.assertEqual(result["updated_count"], 1)
            self.assertEqual(script_path.read_text(encoding="utf-8"), new_script)
            self.assertEqual(backup_path.read_text(encoding="utf-8"), old_script)
            self.assertEqual(manifest[0]["script_path"], str(script_path))


if __name__ == "__main__":
    unittest.main()
