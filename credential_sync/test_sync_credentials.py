import json
import tempfile
import unittest
from pathlib import Path

from credential_sync.sync_credentials import (
    ActiveHost,
    CredentialRecord,
    DecisionRow,
    SyncSettings,
    TargetApplicationRecord,
    ValidationError,
    apply_updates,
    build_duplicate_ip_errors,
    build_sync_plan,
    parse_config,
)


class ConfigParsingTest(unittest.TestCase):
    def test_parse_config_accepts_area_name_array(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "\n".join(
                    [
                        "source_db:",
                        "  host: 172.20.2.91",
                        "  port: 5432",
                        "  dbname: fap",
                        "  user: nds",
                        "  password: rt12345%",
                        "target_db:",
                        "  host: 192.168.1.61",
                        "  port: 5432",
                        "  database: fap",
                        "  user: nds",
                        "  password: rt12345%",
                        "sync:",
                        "  allowed_area_names:",
                        "    - 서버",
                        "    - DBMS",
                        "  report_path: report.json",
                    ]
                ),
                encoding="utf-8",
            )

            config = parse_config(config_path)

        self.assertEqual(config.target_db.dbname, "fap")
        self.assertEqual(config.sync.allowed_area_names, ("서버", "DBMS"))
        self.assertEqual(config.sync.exclude_credential_type_ids, (3,))
        self.assertTrue(config.sync.require_same_credential_type)
        self.assertEqual(config.sync.report_path, config_path.parent / "report.json")

    def test_parse_config_rejects_blank_area_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "\n".join(
                    [
                        "source_db:",
                        "  host: 172.20.2.91",
                        "  port: 5432",
                        "  dbname: fap",
                        "  user: nds",
                        "  password: rt12345%",
                        "target_db:",
                        "  host: 192.168.1.61",
                        "  port: 5432",
                        "  dbname: fap",
                        "  user: nds",
                        "  password: rt12345%",
                        "sync:",
                        "  allowed_area_names:",
                        "    - ''",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValidationError, "allowed_area_names"):
                parse_config(config_path)


class SyncPlanningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = SyncSettings(
            exclude_credential_type_ids=(3,),
            require_same_credential_type=True,
            allowed_area_names=("서버",),
            modified_by=None,
            report_path=Path("sync_report.json"),
        )
        self.source_hosts = [
            ActiveHost(host_id=140, host_name="windows_lyh_pc", host_ip="172.20.2.100"),
            ActiveHost(host_id=89, host_name="oracle", host_ip="192.168.1.5"),
            ActiveHost(host_id=17, host_name="172.20.2.1", host_ip="172.20.2.1"),
        ]
        self.source_credentials = {
            140: CredentialRecord(host_id=140, credential_type_id=4, input_data='{"username":"administrator"}'),
            17: CredentialRecord(host_id=17, credential_type_id=3, input_data='{"username":"admin"}'),
        }
        self.target_hosts = [
            ActiveHost(host_id=59, host_name="windows_lyh_pc", host_ip="172.20.2.100"),
            ActiveHost(host_id=69, host_name="OJY-TEST-6", host_ip="192.168.1.5"),
            ActiveHost(host_id=86, host_name="huawei_test", host_ip="172.20.2.1"),
        ]
        self.target_applications = [
            TargetApplicationRecord(
                vars_host_id=59,
                vars_host_name="windows_lyh_pc",
                host_ip="172.20.2.100",
                host_application_id=155,
                area_id=15,
                area_name="서버",
                application_type_id=20,
                application_id=81,
                application_family_id=None,
                application_version=None,
                target_credential_type_id=4,
            ),
            TargetApplicationRecord(
                vars_host_id=69,
                vars_host_name="OJY-TEST-6",
                host_ip="192.168.1.5",
                host_application_id=274,
                area_id=20,
                area_name="DBMS",
                application_type_id=24,
                application_id=108,
                application_family_id=None,
                application_version="10.26",
                target_credential_type_id=2,
            ),
            TargetApplicationRecord(
                vars_host_id=86,
                vars_host_name="huawei_test",
                host_ip="172.20.2.1",
                host_application_id=226,
                area_id=17,
                area_name="네트워크",
                application_type_id=65,
                application_id=115,
                application_family_id=None,
                application_version=None,
                target_credential_type_id=2,
            ),
        ]

    def test_build_sync_plan_applies_area_filter_before_other_skips(self) -> None:
        plan = build_sync_plan(
            source_hosts=self.source_hosts,
            source_credentials=self.source_credentials,
            target_hosts=self.target_hosts,
            target_applications=self.target_applications,
            settings=self.settings,
        )

        decisions = {row.host_application_id: row.decision for row in plan.decision_rows}

        self.assertFalse(plan.blocked)
        self.assertEqual(plan.decision_counts["matched_hai_rows"], 3)
        self.assertEqual(plan.decision_counts["eligible_update"], 1)
        self.assertEqual(plan.decision_counts["skip_area_not_allowed"], 2)
        self.assertEqual(decisions[155], "eligible_update")
        self.assertEqual(decisions[274], "skip_area_not_allowed")
        self.assertEqual(decisions[226], "skip_area_not_allowed")

    def test_build_sync_plan_without_area_filter_uses_source_skip_reasons(self) -> None:
        settings = SyncSettings(
            exclude_credential_type_ids=(3,),
            require_same_credential_type=True,
            allowed_area_names=None,
            modified_by=None,
            report_path=Path("sync_report.json"),
        )

        plan = build_sync_plan(
            source_hosts=self.source_hosts,
            source_credentials=self.source_credentials,
            target_hosts=self.target_hosts,
            target_applications=self.target_applications,
            settings=settings,
        )

        decisions = {row.host_application_id: row.decision for row in plan.decision_rows}

        self.assertEqual(plan.decision_counts["eligible_update"], 1)
        self.assertEqual(plan.decision_counts["skip_source_credential_missing"], 1)
        self.assertEqual(plan.decision_counts["skip_source_credential_type_excluded"], 1)
        self.assertEqual(decisions[274], "skip_source_credential_missing")
        self.assertEqual(decisions[226], "skip_source_credential_type_excluded")

    def test_build_duplicate_ip_errors_blocks_plan(self) -> None:
        duplicated_target_hosts = list(self.target_hosts) + [
            ActiveHost(host_id=999, host_name="duplicate", host_ip="172.20.2.100")
        ]

        plan = build_sync_plan(
            source_hosts=self.source_hosts,
            source_credentials=self.source_credentials,
            target_hosts=duplicated_target_hosts,
            target_applications=self.target_applications,
            settings=self.settings,
        )

        self.assertTrue(plan.blocked)
        self.assertEqual(len(plan.duplicate_ip_errors), 1)
        self.assertEqual(plan.duplicate_ip_errors[0]["system"], "target")
        self.assertEqual(plan.duplicate_ip_errors[0]["host_ip"], "172.20.2.100")


class ApplyUpdatesTest(unittest.TestCase):
    class FakeCursor:
        def __init__(self) -> None:
            self.executed = []
            self.rowcount = 1

        def __enter__(self) -> "ApplyUpdatesTest.FakeCursor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def execute(self, sql, params) -> None:
            self.executed.append((sql, params))
            self.rowcount = 1

    class FakeConnection:
        def __init__(self) -> None:
            self.cursor_instance = ApplyUpdatesTest.FakeCursor()

        def cursor(self) -> "ApplyUpdatesTest.FakeCursor":
            return self.cursor_instance

    def test_apply_updates_uses_modified_by_when_present(self) -> None:
        connection = self.FakeConnection()
        updates = [
            DecisionRow(
                ip="192.168.1.123",
                fap_host_id=141,
                fap_host_name="RTNET_B1_FILESVR",
                source_credential_type_id=2,
                vars_host_id=60,
                vars_host_name="RTNET_B1_TEST",
                host_application_id=255,
                area_id=15,
                area_name="서버",
                application_type_id=19,
                application_id=69,
                application_family_id=None,
                application_version="8",
                target_credential_type_id=2,
                decision="eligible_update",
                source_input_data='{"username":"fap"}',
            )
        ]

        applied_updates = apply_updates(connection, updates, modified_by=52)

        self.assertEqual(applied_updates, 1)
        self.assertEqual(len(connection.cursor_instance.executed), 1)
        sql, params = connection.cursor_instance.executed[0]
        self.assertIn("modified_by = %s", sql)
        self.assertEqual(params, ('{"username":"fap"}', 52, 255))

    def test_apply_updates_keeps_existing_modified_by_when_missing(self) -> None:
        connection = self.FakeConnection()
        updates = [
            DecisionRow(
                ip="172.20.2.100",
                fap_host_id=140,
                fap_host_name="windows_lyh_pc",
                source_credential_type_id=4,
                vars_host_id=59,
                vars_host_name="windows_lyh_pc",
                host_application_id=155,
                area_id=15,
                area_name="서버",
                application_type_id=20,
                application_id=81,
                application_family_id=None,
                application_version=None,
                target_credential_type_id=4,
                decision="eligible_update",
                source_input_data='{"username":"administrator"}',
            )
        ]

        applied_updates = apply_updates(connection, updates, modified_by=None)

        self.assertEqual(applied_updates, 1)
        sql, params = connection.cursor_instance.executed[0]
        self.assertNotIn("modified_by = %s", sql)
        self.assertEqual(params, ('{"username":"administrator"}', 155))


if __name__ == "__main__":
    unittest.main()
