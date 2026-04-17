import tempfile
import unittest
from pathlib import Path
from typing import Set

from report.generate_report import (
    DefaultInspectionReportGenerator,
    PreventiveInspectionReportGenerator,
    build_mock_report_rows,
    build_output_path,
    build_split_output_path,
    build_result_payload,
    chunk_sequence,
    compute_overview_metrics,
    extract_row_list,
    format_importance,
    get_report_generator,
    load_api_config,
    normalize_output_name,
    normalize_sheet_name,
    parse_args,
)
from report.generate_report import DetailRow, SummaryRow


class GenerateReportHelpersTest(unittest.TestCase):
    def test_load_api_config_reads_api_server_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "fap.conf"
            path.write_text(
                "\n".join(
                    [
                        "[API_SERVER]",
                        "API_URL = https://192.168.1.61:9000",
                        "API_TOKEN = secret-token",
                    ]
                ),
                encoding="utf-8",
            )

            api_url, api_token = load_api_config(path)

        self.assertEqual(api_url, "https://192.168.1.61:9000")
        self.assertEqual(api_token, "secret-token")

    def test_normalize_sheet_name_sanitizes_and_deduplicates(self) -> None:
        used_names = set()  # type: Set[str]

        first_name = normalize_sheet_name("host/name:alpha?beta*", used_names)
        second_name = normalize_sheet_name("host/name:alpha?beta*", used_names)

        self.assertEqual(first_name, "host_name_alpha_beta_")
        self.assertEqual(second_name, "host_name_alpha_beta__1")

    def test_build_result_payload_contains_required_keys(self) -> None:
        payload = build_result_payload(
            result="success",
            report_path="/tmp/report.xlsx",
            msg="ok",
            job_id=123,
            report_type="default",
        )

        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["report_path"], "/tmp/report.xlsx")
        self.assertEqual(payload["msg"], "ok")
        self.assertEqual(payload["job_id"], 123)
        self.assertEqual(payload["report_type"], "default")
        self.assertIn("generated_at", payload)

    def test_extract_row_list_accepts_bare_list(self) -> None:
        rows = extract_row_list([{"a": 1}, {"a": 2}], "summary")
        self.assertEqual(rows, [{"a": 1}, {"a": 2}])

    def test_extract_row_list_accepts_wrapped_list(self) -> None:
        rows = extract_row_list({"data": [{"a": 1}]}, "detail")
        self.assertEqual(rows, [{"a": 1}])

    def test_build_result_payload_includes_user_id_when_present(self) -> None:
        payload = build_result_payload(
            result="success",
            report_path="/tmp/report.xlsx",
            msg="ok",
            job_id=123,
            report_type="default",
            user_id="sysadm",
        )

        self.assertEqual(payload["user_id"], "sysadm")

    def test_detail_row_from_mapping_defaults_preventive_fields_to_empty_strings(self) -> None:
        row = DetailRow.from_mapping({"job_id": 10, "host_id": 1, "host_name": "host-a", "host_ip": "10.0.0.1"})

        self.assertEqual(row.description, "")
        self.assertEqual(row.inspection_command, "")
        self.assertEqual(row.is_service_affect, "")
        self.assertEqual(row.action_content, "")

    def test_compute_overview_metrics_matches_readme_summary_rules(self) -> None:
        rows = [
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time=None,
                finished_time=None,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                host_status="done",
                total_items=10,
                vuln_items=2,
                error_items=1,
                score=90.0,
                host_started=None,
                host_finished=None,
                duration_sec=10,
                error_message="",
            ),
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time=None,
                finished_time=None,
                host_id=2,
                host_name="host-b",
                host_ip="10.0.0.2",
                host_status="done",
                total_items=8,
                vuln_items=1,
                error_items=2,
                score=80.0,
                host_started=None,
                host_finished=None,
                duration_sec=12,
                error_message="",
            ),
        ]

        detail_rows = [
            DetailRow(
                job_id=10,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                inspection_item_name="SSH 설정",
                type_name="계정관리",
                category_name="패스워드",
                area_name="시스템",
                importance="1",
                is_required=True,
                application_type_name="",
                application_name="",
                application_version="",
                result_status="PASS",
                message="ok",
                raw_output="raw",
                description="desc",
                inspection_command="cmd",
                is_service_affect="무",
                action_content="action",
                checked_time=None,
            ),
            DetailRow(
                job_id=10,
                host_id=2,
                host_name="host-b",
                host_ip="10.0.0.2",
                inspection_item_name="계정 잠금",
                type_name="계정관리",
                category_name="인증",
                area_name="시스템",
                importance="2",
                is_required=True,
                application_type_name="",
                application_name="",
                application_version="",
                result_status="취약",
                message="warn",
                raw_output="raw",
                description="desc",
                inspection_command="cmd",
                is_service_affect="유",
                action_content="action",
                checked_time=None,
            ),
            DetailRow(
                job_id=10,
                host_id=2,
                host_name="host-b",
                host_ip="10.0.0.2",
                inspection_item_name="로깅 설정",
                type_name="로그관리",
                category_name="감사",
                area_name="시스템",
                importance="3",
                is_required=True,
                application_type_name="",
                application_name="",
                application_version="",
                result_status="양호",
                message="ok",
                raw_output="raw",
                description="desc",
                inspection_command="cmd",
                is_service_affect="무",
                action_content="action",
                checked_time=None,
            ),
        ]

        metrics = compute_overview_metrics(rows, detail_rows)

        self.assertEqual(metrics.job_id, 10)
        self.assertEqual(metrics.category_type_name, "Linux")
        self.assertAlmostEqual(metrics.average_score, 85.0)
        self.assertAlmostEqual(metrics.average_total_items, 9.0)
        self.assertAlmostEqual(metrics.average_good_items, 1.5)
        self.assertAlmostEqual(metrics.average_vuln_items, 1.5)
        self.assertAlmostEqual(metrics.average_not_run_items, 6.0)
        self.assertEqual(metrics.target_count, 2)
        self.assertEqual(metrics.type_count, 2)

    def test_load_api_config_requires_url_and_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "fap.conf"
            path.write_text(
                "\n".join(
                    [
                        "[API_SERVER]",
                        "API_URL = https://192.168.1.61:9000",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "missing API_URL or API_TOKEN"):
                load_api_config(path)

    def test_format_importance_maps_numeric_levels(self) -> None:
        self.assertEqual(format_importance("1"), "하")
        self.assertEqual(format_importance(2), "중")
        self.assertEqual(format_importance("3"), "상")
        self.assertEqual(format_importance("critical"), "critical")

    def test_get_report_generator_supports_preventive(self) -> None:
        self.assertIsInstance(get_report_generator("preventive"), PreventiveInspectionReportGenerator)

    def test_parse_args_uses_default_output_name(self) -> None:
        args = parse_args(["--job-id", "10"])

        self.assertEqual(args.output_name, "점검보고서")
        self.assertEqual(args.mock_host_count, 0)
        self.assertEqual(args.mock_items_per_host, 3)

    def test_normalize_output_name_uses_filename_stem(self) -> None:
        self.assertEqual(normalize_output_name("custom.xlsx"), "custom")
        self.assertEqual(normalize_output_name(" nested "), "nested")
        self.assertEqual(normalize_output_name(""), "점검보고서")

    def test_build_output_path_uses_output_name_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = build_output_path("custom_report.xlsx", tmp_dir)

        self.assertTrue(output_path.name.startswith("custom_report_"))
        self.assertTrue(output_path.name.endswith(".xlsx"))

    def test_build_split_output_path_appends_part_suffix(self) -> None:
        output_path = Path("/tmp/report.xlsx")

        split_path = build_split_output_path(output_path, 2, 12)

        self.assertEqual(split_path.name, "report_part02.xlsx")

    def test_chunk_sequence_splits_items_by_requested_size(self) -> None:
        chunks = chunk_sequence([1, 2, 3, 4, 5], 2)

        self.assertEqual(chunks, [[1, 2], [3, 4], [5]])

    def test_build_mock_report_rows_generates_requested_hosts_and_items(self) -> None:
        summary_rows, detail_rows = build_mock_report_rows(job_id=999, host_count=4, items_per_host=2)

        self.assertEqual(len(summary_rows), 4)
        self.assertEqual(len(detail_rows), 8)
        self.assertEqual(summary_rows[0].host_name, "MOCK-HOST-001")
        self.assertEqual(detail_rows[0].host_name, "MOCK-HOST-001")
        self.assertEqual(detail_rows[-1].host_name, "MOCK-HOST-004")

    def test_build_workbook_applies_requested_layout(self) -> None:
        summary_rows = [
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time=None,
                finished_time=None,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                host_status="done",
                total_items=10,
                vuln_items=2,
                error_items=1,
                score=90.0,
                host_started=None,
                host_finished=None,
                duration_sec=10,
                error_message="ignored",
            )
        ]
        detail_rows = [
            DetailRow(
                job_id=10,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                inspection_item_name="SSH 설정",
                type_name="계정관리",
                category_name="패스워드",
                area_name="시스템",
                importance="1",
                is_required=True,
                application_type_name="",
                application_name="",
                application_version="",
                result_status="PASS",
                message="ok",
                raw_output="raw",
                description="desc",
                inspection_command="cmd",
                is_service_affect="무",
                action_content="action",
                checked_time=None,
            ),
            DetailRow(
                job_id=10,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                inspection_item_name="로그 설정",
                type_name="로그관리",
                category_name="감사",
                area_name="보안",
                importance="3",
                is_required=True,
                application_type_name="",
                application_name="",
                application_version="",
                result_status="FAIL",
                message="warn",
                raw_output="raw-2",
                description="desc-2",
                inspection_command="cmd-2",
                is_service_affect="유",
                action_content="action-2",
                checked_time=None,
            )
        ]

        workbook = DefaultInspectionReportGenerator().build_workbook(summary_rows, detail_rows)
        summary_sheet = workbook["요약"]
        detail_sheet = workbook["host-a"]

        self.assertAlmostEqual(summary_sheet.column_dimensions["A"].width, 6.88)
        self.assertAlmostEqual(summary_sheet.column_dimensions["J"].width, 12.13)
        self.assertEqual(summary_sheet["A1"].value, "점검 보고서")
        self.assertEqual(summary_sheet["A1"].alignment.horizontal, "center")
        self.assertEqual(summary_sheet["A2"].value, "작업 정보")
        self.assertEqual(summary_sheet["B3"].value, "작업번호")
        self.assertEqual(summary_sheet["C3"].value, 10)
        self.assertEqual(summary_sheet["F3"].value, "점검 대상")
        self.assertEqual(summary_sheet["G3"].value, 1)
        self.assertEqual(summary_sheet["H3"].value, "점검 유형")
        self.assertEqual(summary_sheet["I3"].value, 2)
        self.assertEqual(summary_sheet["A4"].value, "평균 지표")
        self.assertEqual(summary_sheet["B5"].value, "점수")
        self.assertEqual(summary_sheet["C5"].value, 90.0)
        self.assertEqual(summary_sheet["C5"].number_format, "0.0")
        self.assertEqual(summary_sheet["D5"].value, "항목")
        self.assertEqual(summary_sheet["E5"].value, 10.0)
        self.assertEqual(summary_sheet["E5"].number_format, "0.0")
        self.assertEqual(summary_sheet["F5"].value, "양호")
        self.assertEqual(summary_sheet["G5"].value, 2.0)
        self.assertEqual(summary_sheet["G5"].number_format, "0.0")
        self.assertEqual(summary_sheet["H5"].value, "취약")
        self.assertEqual(summary_sheet["I5"].value, 1.0)
        self.assertEqual(summary_sheet["I5"].number_format, "0.0")
        self.assertEqual(summary_sheet["J5"].value, "미실행")
        self.assertEqual(summary_sheet["K5"].value, 7.0)
        self.assertEqual(summary_sheet["K5"].number_format, "0.0")
        self.assertEqual(summary_sheet["D7"].value, "유형")
        self.assertEqual(summary_sheet["E7"].value, "점수")
        self.assertEqual(summary_sheet["F7"].value, "작업상태")
        self.assertEqual(summary_sheet["E8"].value, 90.0)
        self.assertEqual(summary_sheet["E8"].number_format, "0.00")
        self.assertEqual(summary_sheet["F8"].value, "done")
        self.assertEqual(detail_sheet["A2"].value, "host-a 상세 점검    점검 항목 개수: 2    전체 성공률: 50%    상/중/하 성공률: 0%/-/100%")
        self.assertEqual(detail_sheet["A3"].value, "유형 목록: 계정관리, 로그관리    영역 목록: 보안, 시스템    중요도(상/중/하): 1/0/1    PASS: 1    FAIL: 1")
        self.assertTrue(detail_sheet["A3"].font.bold)
        self.assertFalse(detail_sheet["A3"].font.italic)
        self.assertEqual(detail_sheet["A5"].value, "유형")
        self.assertEqual(detail_sheet["D6"].value, "하")
        self.assertEqual(detail_sheet["A6"].alignment.horizontal, "left")
        self.assertEqual(detail_sheet["A6"].alignment.vertical, "center")
        self.assertEqual(detail_sheet["D6"].fill.fgColor.rgb, "00D9EAD3")
        self.assertEqual(detail_sheet["F6"].fill.fgColor.rgb, "00DDEBF7")

    def test_preventive_build_workbook_applies_block_layout(self) -> None:
        summary_rows = [
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time=None,
                finished_time=None,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                host_status="done",
                total_items=10,
                vuln_items=2,
                error_items=1,
                score=90.0,
                host_started=None,
                host_finished=None,
                duration_sec=10,
                error_message="ignored",
            )
        ]
        detail_rows = [
            DetailRow(
                job_id=10,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                inspection_item_name="SSH 설정",
                type_name="계정관리",
                category_name="패스워드",
                area_name="시스템",
                importance="1",
                is_required=True,
                application_type_name="system",
                application_name="sshd",
                application_version="9.7",
                result_status="PASS",
                message="message text",
                raw_output="raw output " * 40,
                description="description text",
                inspection_command="cat /etc/ssh/sshd_config",
                is_service_affect="무",
                action_content="action content " * 20,
                checked_time=None,
            ),
            DetailRow(
                job_id=10,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                inspection_item_name="로그 설정",
                type_name="로그관리",
                category_name="감사",
                area_name="보안",
                importance="3",
                is_required=True,
                application_type_name="service",
                application_name="rsyslog",
                application_version="8.24",
                result_status="FAIL",
                message="warn text",
                raw_output="raw-2",
                description="desc-2",
                inspection_command="cat /etc/rsyslog.conf",
                is_service_affect="유",
                action_content="action-2",
                checked_time=None,
            ),
        ]

        workbook = PreventiveInspectionReportGenerator().build_workbook(summary_rows, detail_rows)
        summary_sheet = workbook["요약"]
        detail_sheet = workbook["host-a"]

        self.assertEqual(summary_sheet["A1"].value, "점검 보고서")
        self.assertEqual(detail_sheet["A1"].value, "요약으로 돌아가기")
        self.assertEqual(detail_sheet.freeze_panes, "A5")
        self.assertEqual(detail_sheet["A2"].value, "host-a 상세 점검    점검 항목 개수: 2    전체 성공률: 50%    상/중/하 성공률: 0%/-/100%")
        self.assertEqual(detail_sheet["A5"].value, "유형")
        self.assertEqual(detail_sheet["B5"].value, "계정관리")
        self.assertEqual(detail_sheet["A6"].value, "애플리케이션유형")
        self.assertEqual(detail_sheet["B6"].value, "system")
        self.assertEqual(detail_sheet["D6"].value, "애플리케이션명")
        self.assertEqual(detail_sheet["E6"].value, "sshd")
        self.assertEqual(detail_sheet["G6"].value, "버전")
        self.assertEqual(detail_sheet["H6"].value, "9.7")
        self.assertEqual(detail_sheet["A7"].value, "점검결과")
        self.assertEqual(detail_sheet["B7"].value, "PASS")
        self.assertEqual(detail_sheet["E7"].value, "중요도")
        self.assertEqual(detail_sheet["F7"].value, "하")
        self.assertEqual(detail_sheet["B7"].fill.fgColor.rgb, "00DDEBF7")
        self.assertEqual(detail_sheet["F7"].fill.fgColor.rgb, "00D9EAD3")
        self.assertEqual(detail_sheet["A10"].value, "상세")
        self.assertEqual(detail_sheet["A11"].value, "메세지")
        self.assertEqual(detail_sheet["A12"].value, "설명")
        self.assertEqual(detail_sheet["A13"].value, "서비스 영향 유/무")
        self.assertEqual(detail_sheet["B13"].value, "무")
        self.assertEqual(detail_sheet["A14"].value, "조치내역")
        self.assertGreater(detail_sheet.row_dimensions[10].height, 36)
        self.assertGreater(detail_sheet.row_dimensions[14].height, 36)
        self.assertIsNone(detail_sheet["A15"].value)
        self.assertIsNone(detail_sheet["A16"].value)
        self.assertEqual(detail_sheet["A17"].value, "유형")
        self.assertEqual(detail_sheet["B17"].value, "로그관리")

    def test_preventive_build_workbook_shows_empty_message_when_detail_missing(self) -> None:
        summary_rows = [
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time=None,
                finished_time=None,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                host_status="done",
                total_items=10,
                vuln_items=2,
                error_items=1,
                score=90.0,
                host_started=None,
                host_finished=None,
                duration_sec=10,
                error_message="",
            )
        ]

        workbook = PreventiveInspectionReportGenerator().build_workbook(summary_rows, [])
        detail_sheet = workbook["host-a"]

        self.assertEqual(detail_sheet["A5"].value, "상세 데이터가 없습니다.")

    def test_build_workbook_creates_one_detail_sheet_per_host(self) -> None:
        duplicate_host_rows = [
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time=None,
                finished_time=None,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                host_status="done",
                total_items=10,
                vuln_items=2,
                error_items=1,
                score=90.0,
                host_started=None,
                host_finished=None,
                duration_sec=10,
                error_message="",
            ),
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time=None,
                finished_time=None,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                host_status="done",
                total_items=10,
                vuln_items=2,
                error_items=1,
                score=90.0,
                host_started=None,
                host_finished=None,
                duration_sec=10,
                error_message="",
            ),
        ]

        workbook = DefaultInspectionReportGenerator().build_workbook(duplicate_host_rows, [])

        self.assertEqual(workbook.sheetnames, ["요약", "host-a"])

    def test_save_workbooks_splits_when_sheet_limit_is_exceeded(self) -> None:
        summary_rows = []
        for host_index in range(1, 4):
            summary_rows.append(
                SummaryRow(
                    job_id=10,
                    category_type_name="Linux",
                    run_status="done",
                    started_time=None,
                    finished_time=None,
                    host_id=host_index,
                    host_name=f"host-{host_index}",
                    host_ip=f"10.0.0.{host_index}",
                    host_status="done",
                    total_items=10,
                    vuln_items=2,
                    error_items=1,
                    score=90.0,
                    host_started=None,
                    host_finished=None,
                    duration_sec=10,
                    error_message="",
                )
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            saved_paths = DefaultInspectionReportGenerator().save_workbooks(
                summary_rows,
                [],
                Path(tmp_dir) / "report.xlsx",
                max_sheets_per_workbook=3,
            )

        self.assertEqual(len(saved_paths), 2)
        self.assertEqual(saved_paths[0].name, "report_part01.xlsx")
        self.assertEqual(saved_paths[1].name, "report_part02.xlsx")


if __name__ == "__main__":
    unittest.main()
