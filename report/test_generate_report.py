from io import BytesIO
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Set

from report.generate_report import (
    DefaultInspectionReportGenerator,
    GovernmentChecklistReportGenerator,
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
    classify_detail_result_status,
    load_api_config,
    normalize_output_name,
    normalize_sheet_name,
    parse_args,
    save_preventive_hwpx_reports,
    save_government_checklist_docx_reports,
)
from report.generate_report import DetailRow, SummaryRow


HWPX_HP_TAG = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"


def make_summary_row(host_id: int, host_name: str, host_ip: Optional[str] = None) -> SummaryRow:
    return SummaryRow(
        job_id=10,
        category_type_name="Linux",
        run_status="done",
        started_time="2026-03-17 08:00:00",
        finished_time=None,
        host_id=host_id,
        host_name=host_name,
        host_ip=host_ip or f"10.0.0.{host_id}",
        host_status="done",
        total_items=3,
        vuln_items=1,
        error_items=1,
        score=80.0,
        host_started="2026-03-17 09:00:00",
        host_finished=None,
        duration_sec=10,
        error_message="",
    )


def make_detail_row(
    host_id: int,
    host_name: str,
    area_name: str,
    inspection_code: str,
    inspection_item_name: str,
    result_status: str,
    message: str,
    *,
    checked_time: str = "2026-03-17 09:30:00",
) -> DetailRow:
    return DetailRow(
        job_id=10,
        host_id=host_id,
        host_name=host_name,
        host_ip=f"10.0.0.{host_id}",
        inspection_code=inspection_code,
        inspection_item_name=inspection_item_name,
        type_name="계정관리",
        category_name="패스워드",
        area_name=area_name,
        importance="1",
        is_required=True,
        application_type_name="system",
        application_name="sshd",
        application_version="9.7",
        result_status=result_status,
        message=message,
        raw_output="raw",
        description="desc",
        inspection_command="cmd",
        is_service_affect="무",
        action_content="",
        checked_time=checked_time,
    )


def get_hwpx_row_cell_texts(section_xml: str, item_label: str) -> List[str]:
    root = ET.fromstring(section_xml)
    for row in root.iter(HWPX_HP_TAG + "tr"):
        cells = row.findall(HWPX_HP_TAG + "tc")
        cell_texts = [get_hwpx_cell_text(cell) for cell in cells]
        if any(item_label in cell_text for cell_text in cell_texts):
            return cell_texts
    return []


def get_hwpx_cell_text(cell: ET.Element) -> str:
    paragraphs = list(cell.iter(HWPX_HP_TAG + "p"))
    if paragraphs:
        return "\n".join("".join(paragraph.itertext()) for paragraph in paragraphs)
    return "".join(cell.itertext())


def get_hwpx_row_cell_heights(section_xml: str, item_label: str) -> List[int]:
    root = ET.fromstring(section_xml)
    for row in root.iter(HWPX_HP_TAG + "tr"):
        cells = row.findall(HWPX_HP_TAG + "tc")
        cell_texts = [get_hwpx_cell_text(cell) for cell in cells]
        if any(item_label in cell_text for cell_text in cell_texts):
            heights = []
            for cell in cells:
                cell_size = cell.find(HWPX_HP_TAG + "cellSz")
                heights.append(int(cell_size.get("height")) if cell_size is not None else 0)
            return heights
    return []


def count_hwpx_blank_paragraphs_between_table_and_summary(section_xml: str) -> int:
    root = ET.fromstring(section_xml)
    found_table = False
    blank_count = 0
    for child in list(root):
        if not found_table:
            found_table = child.find(".//" + HWPX_HP_TAG + "tbl") is not None
            continue

        text = "".join(text_element.text or "" for text_element in child.iter(HWPX_HP_TAG + "t"))
        if "점검 결과 요약" in text:
            return blank_count
        if (
            child.tag == HWPX_HP_TAG + "p"
            and child.find(".//" + HWPX_HP_TAG + "tbl") is None
            and not text.strip()
        ):
            blank_count += 1
    return blank_count


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
                inspection_code="LIN-001",
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
                inspection_code="LIN-002",
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
                inspection_code="LIN-003",
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

    def test_classify_detail_result_status_treats_warn_as_failed(self) -> None:
        self.assertEqual(classify_detail_result_status("WARN"), "fail")
        self.assertEqual(classify_detail_result_status("warning"), "fail")

    def test_get_report_generator_does_not_route_preventive_to_excel(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported report type: preventive"):
            get_report_generator("preventive")

    def test_get_report_generator_uses_government_checklist_for_default(self) -> None:
        self.assertIsInstance(get_report_generator("default"), GovernmentChecklistReportGenerator)

    def test_get_report_generator_supports_government_checklist(self) -> None:
        self.assertIsInstance(get_report_generator("government-checklist"), GovernmentChecklistReportGenerator)

    def test_parse_args_uses_default_output_name(self) -> None:
        args = parse_args(["--job-id", "10"])

        self.assertEqual(args.output_name, "점검보고서")
        self.assertEqual(args.output_format, "xlsx")
        self.assertEqual(args.mock_host_count, 0)
        self.assertEqual(args.mock_items_per_host, 3)

    def test_parse_args_accepts_docx_output_format(self) -> None:
        args = parse_args(["--job-id", "10", "--output-format", "docx"])

        self.assertEqual(args.output_format, "docx")

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
                inspection_code="LIN-001",
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
                inspection_code="LIN-002",
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
        self.assertEqual(detail_sheet["E6"].value, "LIN-001")
        self.assertEqual(detail_sheet["F6"].value, "SSH 설정")
        self.assertEqual(detail_sheet["G6"].value, "PASS")
        self.assertEqual(detail_sheet["A6"].alignment.horizontal, "left")
        self.assertEqual(detail_sheet["A6"].alignment.vertical, "center")
        self.assertEqual(detail_sheet["D6"].fill.fgColor.rgb, "00D9EAD3")
        self.assertEqual(detail_sheet["G6"].fill.fgColor.rgb, "00DDEBF7")

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
                inspection_code="LIN-001",
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
                inspection_code="LIN-002",
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
        self.assertEqual(detail_sheet["D7"].value, "중요도")
        self.assertEqual(detail_sheet["E7"].value, "하")
        self.assertEqual(detail_sheet["G7"].value, "점검코드")
        self.assertEqual(detail_sheet["H7"].value, "LIN-001")
        self.assertEqual(detail_sheet["B7"].fill.fgColor.rgb, "00DDEBF7")
        self.assertEqual(detail_sheet["E7"].fill.fgColor.rgb, "00D9EAD3")
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

    def test_government_checklist_build_workbook_uses_checklist_summary_and_preventive_details(self) -> None:
        summary_rows = [
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time="2026-03-17 08:00:00",
                finished_time=None,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                host_status="done",
                total_items=3,
                vuln_items=1,
                error_items=1,
                score=80.0,
                host_started="2026-03-17 09:00:00",
                host_finished=None,
                duration_sec=10,
                error_message="",
            ),
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time="2026-03-17 08:10:00",
                finished_time=None,
                host_id=2,
                host_name="host-b",
                host_ip="10.0.0.2",
                host_status="done",
                total_items=1,
                vuln_items=1,
                error_items=0,
                score=100.0,
                host_started=None,
                host_finished=None,
                duration_sec=10,
                error_message="",
            ),
            SummaryRow(
                job_id=10,
                category_type_name="Linux",
                run_status="done",
                started_time="2026-03-17 08:20:00",
                finished_time=None,
                host_id=3,
                host_name="host-c",
                host_ip="10.0.0.3",
                host_status="done",
                total_items=1,
                vuln_items=1,
                error_items=0,
                score=100.0,
                host_started=None,
                host_finished=None,
                duration_sec=10,
                error_message="",
            ),
        ]
        detail_rows = [
            DetailRow(
                job_id=10,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                inspection_code="LIN-001",
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
                message="ok",
                raw_output="raw",
                description="desc",
                inspection_command="cmd",
                is_service_affect="무",
                action_content="",
                checked_time=None,
            ),
            DetailRow(
                job_id=10,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                inspection_code="LIN-002",
                inspection_item_name="로그 설정",
                type_name="로그관리",
                category_name="감사",
                area_name="보안",
                importance="3",
                is_required=True,
                application_type_name="service",
                application_name="rsyslog",
                application_version="8.24",
                result_status="취약",
                message="warn",
                raw_output="raw-2",
                description="desc-2",
                inspection_command="cmd-2",
                is_service_affect="유",
                action_content="조치-1",
                checked_time=None,
            ),
            DetailRow(
                job_id=10,
                host_id=1,
                host_name="host-a",
                host_ip="10.0.0.1",
                inspection_code="LIN-003",
                inspection_item_name="백업 설정",
                type_name="백업관리",
                category_name="백업",
                area_name="시스템",
                importance="2",
                is_required=True,
                application_type_name="service",
                application_name="backup",
                application_version="1.0",
                result_status="미실행",
                message="skip",
                raw_output="raw-3",
                description="desc-3",
                inspection_command="cmd-3",
                is_service_affect="무",
                action_content="조치-2",
                checked_time=None,
            ),
            DetailRow(
                job_id=10,
                host_id=2,
                host_name="host-b",
                host_ip="10.0.0.2",
                inspection_code="LIN-001",
                inspection_item_name="SSH 설정",
                type_name="계정관리",
                category_name="패스워드",
                area_name="시스템",
                importance="1",
                is_required=True,
                application_type_name="system",
                application_name="sshd",
                application_version="9.7",
                result_status="취약",
                message="warn",
                raw_output="raw",
                description="desc",
                inspection_command="cmd",
                is_service_affect="무",
                action_content="조치-1",
                checked_time="2026-03-17 09:20:00",
            ),
            DetailRow(
                job_id=10,
                host_id=2,
                host_name="host-b",
                host_ip="10.0.0.2",
                inspection_code="LIN-003",
                inspection_item_name="백업 설정",
                type_name="백업관리",
                category_name="백업",
                area_name="시스템",
                importance="2",
                is_required=True,
                application_type_name="service",
                application_name="backup",
                application_version="1.0",
                result_status="ok",
                message="ok-b",
                raw_output="raw",
                description="desc",
                inspection_command="cmd",
                is_service_affect="무",
                action_content="",
                checked_time="2026-03-17 09:21:00",
            ),
            DetailRow(
                job_id=10,
                host_id=3,
                host_name="host-c",
                host_ip="10.0.0.3",
                inspection_code="LIN-001",
                inspection_item_name="SSH 설정",
                type_name="계정관리",
                category_name="패스워드",
                area_name="시스템",
                importance="1",
                is_required=True,
                application_type_name="system",
                application_name="sshd",
                application_version="9.7",
                result_status="ok",
                message="ok-c",
                raw_output="raw",
                description="desc",
                inspection_command="cmd",
                is_service_affect="무",
                action_content="",
                checked_time="2026-03-17 09:22:00",
            ),
        ]

        workbook = GovernmentChecklistReportGenerator().build_workbook(summary_rows, detail_rows)
        summary_sheet = workbook["요약"]
        detail_sheet = workbook["host-a"]

        self.assertEqual(summary_sheet.page_setup.orientation, "portrait")
        self.assertEqual(summary_sheet["A1"].value, "시스템 점검 일지")
        self.assertEqual(summary_sheet["A2"].value, "□ 시스템 점검")
        self.assertEqual(summary_sheet["A3"].value, "○ 장비명: host-a, host-b, host-c")
        self.assertEqual(summary_sheet["A4"].value, "○ 점검 일자: 2026-03-17 09:00:00")
        self.assertEqual(
            [summary_sheet.cell(row=5, column=column).value for column in range(1, 6)],
            ["번호", "점검항목", "host-a", None, None],
        )
        self.assertEqual(summary_sheet["F5"].value, "host-b")
        self.assertEqual(summary_sheet["I5"].value, "host-c")
        self.assertEqual(
            [summary_sheet.cell(row=6, column=column).value for column in range(3, 12)],
            ["정상", "비정상", "비고", "정상", "비정상", "비고", "정상", "비정상", "비고"],
        )
        self.assertEqual(
            [summary_sheet.cell(row=row, column=2).value for row in range(7, 9)],
            ["SSH 설정", "백업 설정"],
        )
        self.assertEqual(
            (summary_sheet["C7"].value, summary_sheet["D7"].value, summary_sheet["E7"].value),
            ("[✔]", "[ ]", "ok"),
        )
        self.assertEqual(
            (summary_sheet["F7"].value, summary_sheet["G7"].value, summary_sheet["H7"].value),
            ("[ ]", "[✔]", "warn"),
        )
        self.assertEqual(
            (summary_sheet["I7"].value, summary_sheet["J7"].value, summary_sheet["K7"].value),
            ("[✔]", "[ ]", "ok-c"),
        )
        self.assertEqual(
            (summary_sheet["C8"].value, summary_sheet["D8"].value, summary_sheet["E8"].value),
            ("[ ]", "[ ]", "skip\n결과: 미실행"),
        )
        self.assertEqual(
            (summary_sheet["F8"].value, summary_sheet["G8"].value, summary_sheet["H8"].value),
            ("[✔]", "[ ]", "ok-b"),
        )
        self.assertEqual(
            (summary_sheet["I8"].value, summary_sheet["J8"].value, summary_sheet["K8"].value),
            ("[ ]", "[ ]", "-"),
        )
        self.assertEqual(summary_sheet["A9"].value, "□ 점검 결과 요약")
        self.assertEqual(summary_sheet["A10"].value, "총 5건 / 정상 3건 / 비정상 1건 / 확인필요 1건")
        self.assertEqual(summary_sheet["A11"].value, "□ 주요 조치내역")
        self.assertEqual(summary_sheet["A12"].value, "1. host-a: 조치-2\n2. host-b: 조치-1")
        self.assertEqual(summary_sheet["A13"].value, "점검자")
        self.assertEqual(summary_sheet["J13"].value, "확인자")
        self.assertEqual(summary_sheet["A16"].value, "보안 점검 일지")
        self.assertEqual(summary_sheet["A17"].value, "□ 보안 점검")
        self.assertEqual(summary_sheet["B22"].value, "로그 설정")
        self.assertEqual(summary_sheet["D22"].value, "[✔]")
        self.assertEqual(detail_sheet["A1"].value, "요약으로 돌아가기")
        self.assertEqual(detail_sheet.freeze_panes, "A5")
        self.assertEqual(detail_sheet["A5"].value, "유형")
        self.assertEqual(detail_sheet["A6"].value, "애플리케이션유형")

    def test_save_government_checklist_docx_reports_writes_one_document_per_area(self) -> None:
        summary_rows, detail_rows = build_mock_report_rows(job_id=10, host_count=2, items_per_host=2)

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = save_government_checklist_docx_reports(
                summary_rows,
                detail_rows,
                Path(tmp_dir) / "점검보고서.docx",
            )
            document_dir = Path(tmp_dir) / "점검보고서"
            docx_paths = sorted(document_dir.glob("*.docx"))

            self.assertEqual(report_path.name, "점검보고서.zip")
            self.assertEqual(len(docx_paths), 2)
            with zipfile.ZipFile(report_path) as zip_handle:
                self.assertEqual(sorted(zip_handle.namelist()), sorted(path.name for path in docx_paths))
            with zipfile.ZipFile(docx_paths[0]) as docx_handle:
                package_names = set(docx_handle.namelist())
                self.assertIn("docProps/core.xml", package_names)
                self.assertIn("docProps/app.xml", package_names)
                self.assertIn("word/_rels/document.xml.rels", package_names)
                self.assertIn("word/settings.xml", package_names)
                self.assertIn("word/fontTable.xml", package_names)
                for package_name in package_names:
                    if package_name.endswith(".xml"):
                        ET.fromstring(docx_handle.read(package_name))
                document_xml = docx_handle.read("word/document.xml").decode("utf-8")

        self.assertIn("영역-1 점검 일지", document_xml)
        self.assertIn("MOCK-HOST-001", document_xml)
        self.assertIn("MOCK-HOST-002", document_xml)
        self.assertIn("정상", document_xml)
        self.assertIn("비정상", document_xml)
        self.assertIn("비고", document_xml)

    def test_save_preventive_hwpx_reports_writes_valid_template_package(self) -> None:
        summary_rows = [make_summary_row(1, "host-a")]
        detail_rows = [
            make_detail_row(1, "host-a", "시스템", "LIN-001", "SSH 설정", "PASS", "ok"),
            make_detail_row(1, "host-a", "시스템", "LIN-002", "로그 설정", "미실행", "skip"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = save_preventive_hwpx_reports(
                summary_rows,
                detail_rows,
                Path(tmp_dir) / "preventive.hwpx",
            )
            with zipfile.ZipFile(report_path) as hwpx_handle:
                package_names = set(hwpx_handle.namelist())
                section_xml = hwpx_handle.read("Contents/section0.xml").decode("utf-8")
                ET.fromstring(section_xml)
                log_row_cells = get_hwpx_row_cell_texts(section_xml, "로그 설정")

        self.assertEqual(report_path.name, "preventive.hwpx")
        self.assertIn("mimetype", package_names)
        self.assertIn("Contents/header.xml", package_names)
        self.assertNotIn("{{", section_xml)
        self.assertIn("시스템 점검 일지", section_xml)
        self.assertIn("host-a", section_xml)
        self.assertIn("SSH 설정", section_xml)
        self.assertIn("로그 설정", section_xml)
        self.assertNotIn("skip", section_xml)
        self.assertNotIn("결과: 미실행", section_xml)
        self.assertEqual(log_row_cells[4], "")
        self.assertIn("정상 1개, 비정상 0개", section_xml)

    def test_save_preventive_hwpx_reports_wraps_long_check_item_text(self) -> None:
        summary_rows = [make_summary_row(1, "host-a")]
        long_item_name = "매우 긴 점검 항목 이름입니다 " * 4
        detail_rows = [
            make_detail_row(1, "host-a", "시스템", "LIN-001", long_item_name, "PASS", "ok"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = save_preventive_hwpx_reports(
                summary_rows,
                detail_rows,
                Path(tmp_dir) / "preventive.hwpx",
            )
            with zipfile.ZipFile(report_path) as hwpx_handle:
                section_xml = hwpx_handle.read("Contents/section0.xml").decode("utf-8")
                row_cells = get_hwpx_row_cell_texts(section_xml, "매우 긴 점검 항목")
                row_heights = get_hwpx_row_cell_heights(section_xml, "매우 긴 점검 항목")

        self.assertIn("매우 긴 점검 항목", section_xml)
        self.assertNotIn("...", section_xml)
        self.assertEqual(" ".join(row_cells[1].split()), long_item_name.strip())
        self.assertIn("\n", row_cells[1])
        self.assertGreater(row_heights[1], 282)

    def test_save_preventive_hwpx_reports_consumes_reserved_space_for_extra_rows(self) -> None:
        summary_rows = [make_summary_row(1, "host-a")]
        one_detail = [make_detail_row(1, "host-a", "시스템", "LIN-001", "SSH 설정", "PASS", "ok")]
        three_details = [
            make_detail_row(1, "host-a", "시스템", "LIN-001", "SSH 설정", "PASS", "ok"),
            make_detail_row(1, "host-a", "시스템", "LIN-002", "로그 설정", "취약", "warn"),
            make_detail_row(1, "host-a", "시스템", "LIN-003", "백업 설정", "PASS", "ok"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            one_detail_path = save_preventive_hwpx_reports(
                summary_rows,
                one_detail,
                Path(tmp_dir) / "one.hwpx",
            )
            three_detail_path = save_preventive_hwpx_reports(
                summary_rows,
                three_details,
                Path(tmp_dir) / "three.hwpx",
            )
            with zipfile.ZipFile(one_detail_path) as hwpx_handle:
                one_detail_xml = hwpx_handle.read("Contents/section0.xml").decode("utf-8")
            with zipfile.ZipFile(three_detail_path) as hwpx_handle:
                three_detail_xml = hwpx_handle.read("Contents/section0.xml").decode("utf-8")

        self.assertEqual(
            count_hwpx_blank_paragraphs_between_table_and_summary(one_detail_xml)
            - count_hwpx_blank_paragraphs_between_table_and_summary(three_detail_xml),
            2,
        )

    def test_save_preventive_hwpx_reports_zips_multiple_area_documents(self) -> None:
        summary_rows = [make_summary_row(1, "host-a")]
        detail_rows = [
            make_detail_row(1, "host-a", "시스템", "LIN-001", "SSH 설정", "PASS", "ok"),
            make_detail_row(1, "host-a", "보안", "LIN-002", "로그 설정", "취약", "warn"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = save_preventive_hwpx_reports(
                summary_rows,
                detail_rows,
                Path(tmp_dir) / "preventive.hwpx",
            )
            with zipfile.ZipFile(report_path) as zip_handle:
                archive_names = sorted(zip_handle.namelist())
                first_hwpx = zip_handle.read(archive_names[0])
            with zipfile.ZipFile(BytesIO(first_hwpx)) as hwpx_handle:
                section_xml = hwpx_handle.read("Contents/section0.xml").decode("utf-8")
                ET.fromstring(section_xml)

        self.assertEqual(report_path.name, "preventive.zip")
        self.assertEqual(len(archive_names), 2)
        self.assertTrue(all(name.endswith(".hwpx") for name in archive_names))
        self.assertNotIn("{{", section_xml)

    def test_save_preventive_hwpx_reports_repeats_hosts_in_same_area(self) -> None:
        summary_rows = [make_summary_row(1, "host-a"), make_summary_row(2, "host-b")]
        detail_rows = [
            make_detail_row(1, "host-a", "시스템", "LIN-001", "SSH 설정", "PASS", "ok"),
            make_detail_row(2, "host-b", "시스템", "LIN-001", "SSH 설정", "취약", "warn"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = save_preventive_hwpx_reports(
                summary_rows,
                detail_rows,
                Path(tmp_dir) / "preventive.hwpx",
            )
            with zipfile.ZipFile(report_path) as hwpx_handle:
                section_xml = hwpx_handle.read("Contents/section0.xml").decode("utf-8")
                root = ET.fromstring(section_xml)

        self.assertEqual(report_path.name, "preventive.hwpx")
        self.assertIn("host-a", section_xml)
        self.assertIn("host-b", section_xml)
        self.assertEqual(section_xml.count("시스템 점검 일지"), 2)
        self.assertEqual(len(root.findall('.//*[@pageBreak="1"]')), 1)

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
