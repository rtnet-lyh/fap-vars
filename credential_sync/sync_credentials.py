#!/usr/bin/env python3

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import psycopg
from psycopg.rows import dict_row
import yaml

TRUTHY_STRINGS = frozenset({"1", "true", "t", "yes", "y", "on"})


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str


@dataclass(frozen=True)
class SyncSettings:
    exclude_credential_type_ids: Tuple[int, ...]
    require_same_credential_type: bool
    allowed_area_names: Optional[Tuple[str, ...]]
    modified_by: Optional[int]
    report_path: Path


@dataclass(frozen=True)
class AppConfig:
    source_db: DatabaseConfig
    target_db: DatabaseConfig
    sync: SyncSettings


@dataclass(frozen=True)
class ActiveHost:
    host_id: int
    host_name: str
    host_ip: str


@dataclass(frozen=True)
class CredentialRecord:
    host_id: int
    credential_type_id: int
    input_data: str


@dataclass(frozen=True)
class TargetApplicationRecord:
    vars_host_id: int
    vars_host_name: str
    host_ip: str
    host_application_id: int
    area_id: Optional[int]
    area_name: Optional[str]
    application_type_id: int
    application_id: int
    application_family_id: Optional[int]
    application_version: Optional[str]
    target_credential_type_id: Optional[int]


@dataclass(frozen=True)
class DecisionRow:
    ip: str
    fap_host_id: int
    fap_host_name: str
    source_credential_type_id: Optional[int]
    vars_host_id: int
    vars_host_name: str
    host_application_id: int
    area_id: Optional[int]
    area_name: Optional[str]
    application_type_id: int
    application_id: int
    application_family_id: Optional[int]
    application_version: Optional[str]
    target_credential_type_id: Optional[int]
    decision: str
    source_input_data: Optional[str]


@dataclass(frozen=True)
class SyncPlan:
    blocked: bool
    duplicate_ip_errors: Tuple[Dict[str, Any], ...]
    host_ip_summary: Dict[str, Any]
    decision_rows: Tuple[DecisionRow, ...]

    @property
    def decision_counts(self) -> Dict[str, int]:
        counts: Counter[str] = Counter()
        for row in self.decision_rows:
            counts["matched_hai_rows"] += 1
            counts[row.decision] += 1
        return dict(counts)

    @property
    def eligible_updates(self) -> Tuple[DecisionRow, ...]:
        return tuple(row for row in self.decision_rows if row.decision == "eligible_update")


@dataclass(frozen=True)
class SyncSummary:
    report_path: Path
    mode: str
    blocked: bool
    matched_hai_rows: int
    eligible_updates: int
    applied_updates: int
    decision_counts: Dict[str, int]
    duplicate_ip_errors: Tuple[Dict[str, Any], ...]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync host credentials from FAP to VARS.")
    parser.add_argument("--config", required=True, help="Path to the YAML config file")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates to the target database. Dry-run is the default.",
    )
    return parser.parse_args(argv)


def load_yaml_config(config_path: Path) -> Mapping[str, Any]:
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValidationError(f"Invalid YAML in config file: {exc}") from exc

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValidationError("Config root must be a YAML mapping")
    return payload


def parse_positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a positive integer")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value.isdigit():
        parsed = int(value)
    else:
        raise ValidationError(f"{field_name} must be a positive integer")

    if parsed < 1:
        raise ValidationError(f"{field_name} must be at least 1")
    return parsed


def normalize_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value in (0, 1):
            return bool(value)
        raise ValidationError(f"{field_name} must be a boolean")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in TRUTHY_STRINGS:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off"}:
            return False
    raise ValidationError(f"{field_name} must be a boolean")


def parse_database_config(raw_value: Any, field_name: str) -> DatabaseConfig:
    if not isinstance(raw_value, dict):
        raise ValidationError(f"{field_name} must be a mapping")

    host = raw_value.get("host")
    user = raw_value.get("user")
    password = raw_value.get("password")
    dbname = raw_value.get("dbname", raw_value.get("database"))

    for item_name, item_value in (
        ("host", host),
        ("user", user),
        ("password", password),
        ("dbname", dbname),
    ):
        if not isinstance(item_value, str) or not item_value.strip():
            raise ValidationError(f"{field_name}.{item_name} must be a non-empty string")

    raw_port = raw_value.get("port", 5432)
    port = parse_positive_int(raw_port, f"{field_name}.port")

    return DatabaseConfig(
        host=host.strip(),
        port=port,
        dbname=dbname.strip(),
        user=user.strip(),
        password=password,
    )


def normalize_area_name(value: Any) -> str:
    if value is None:
        raise ValidationError("allowed_area_names values must be non-empty strings")

    text = str(value).strip()
    if not text:
        raise ValidationError("allowed_area_names values must be non-empty strings")
    return text


def parse_area_names(raw_value: Any) -> Optional[Tuple[str, ...]]:
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        normalized = normalize_area_name(raw_value)
        return (normalized,)
    if not isinstance(raw_value, list):
        raise ValidationError("sync.allowed_area_names must be a string or an array of strings")
    if not raw_value:
        return None

    seen = set()
    normalized_values: List[str] = []
    for item in raw_value:
        normalized = normalize_area_name(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)
    return tuple(normalized_values)


def parse_excluded_type_ids(raw_value: Any) -> Tuple[int, ...]:
    if raw_value is None:
        return (3,)
    if isinstance(raw_value, list):
        if not raw_value:
            return tuple()
        values = tuple(parse_positive_int(item, "sync.exclude_credential_type_ids[]") for item in raw_value)
        return values
    return (parse_positive_int(raw_value, "sync.exclude_credential_type_ids"),)


def resolve_output_path(base_dir: Path, raw_path: Any) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValidationError("sync.report_path must be a non-empty string")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate


def parse_optional_modified_by(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return parse_positive_int(value, "sync.modified_by")


def parse_config(config_path: Path) -> AppConfig:
    resolved_config_path = config_path.resolve(strict=False)
    payload = load_yaml_config(resolved_config_path)
    sync_payload = payload.get("sync", {})

    if sync_payload is None:
        sync_payload = {}
    if not isinstance(sync_payload, dict):
        raise ValidationError("sync must be a mapping")

    return AppConfig(
        source_db=parse_database_config(payload.get("source_db"), "source_db"),
        target_db=parse_database_config(payload.get("target_db"), "target_db"),
        sync=SyncSettings(
            exclude_credential_type_ids=parse_excluded_type_ids(
                sync_payload.get("exclude_credential_type_ids")
            ),
            require_same_credential_type=normalize_bool(
                sync_payload.get("require_same_credential_type", True),
                "sync.require_same_credential_type",
            ),
            allowed_area_names=parse_area_names(sync_payload.get("allowed_area_names")),
            modified_by=parse_optional_modified_by(sync_payload.get("modified_by")),
            report_path=resolve_output_path(
                resolved_config_path.parent,
                sync_payload.get("report_path", "sync_report.json"),
            ),
        ),
    )


def connect_database(config: DatabaseConfig) -> psycopg.Connection[Any]:
    return psycopg.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
        row_factory=dict_row,
    )


def fetch_active_hosts(connection: psycopg.Connection[Any]) -> List[ActiveHost]:
    sql = """
        select
            hi.host_id::int as host_id,
            hi.host_name,
            trim(hi.host_ip) as host_ip
        from host_info hi
        where hi.is_enable = 1
          and coalesce(trim(hi.host_ip), '') <> ''
        order by hi.host_id::int
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [
            ActiveHost(
                host_id=int(row["host_id"]),
                host_name=str(row["host_name"] or ""),
                host_ip=str(row["host_ip"] or "").strip(),
            )
            for row in cursor.fetchall()
        ]


def fetch_source_credentials(connection: psycopg.Connection[Any]) -> Dict[int, CredentialRecord]:
    sql = """
        select
            chi.host_id,
            chi.credential_type_id,
            chi.input_data
        from credential_host_info chi
        join host_info hi
          on hi.host_id::int = chi.host_id
        where hi.is_enable = 1
          and coalesce(trim(hi.host_ip), '') <> ''
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        records: Dict[int, CredentialRecord] = {}
        for row in cursor.fetchall():
            records[int(row["host_id"])] = CredentialRecord(
                host_id=int(row["host_id"]),
                credential_type_id=int(row["credential_type_id"]),
                input_data=str(row["input_data"]),
            )
        return records


def fetch_target_applications(connection: psycopg.Connection[Any]) -> List[TargetApplicationRecord]:
    sql = """
        select
            hi.host_id::int as vars_host_id,
            hi.host_name as vars_host_name,
            trim(hi.host_ip) as host_ip,
            hai.id as host_application_id,
            hai.area_id,
            va.name as area_name,
            hai.application_type_id,
            hai.application_id,
            hai.application_family_id,
            hai.application_version,
            chai.credential_type_id as target_credential_type_id
        from host_info hi
        join host_application_info hai
          on hai.host_id = hi.host_id::int
        left join credential_host_application_info chai
          on chai.host_application_id = hai.id
        left join vars_area va
          on va.id = hai.area_id
        where hi.is_enable = 1
          and coalesce(trim(hi.host_ip), '') <> ''
        order by trim(hi.host_ip), hai.id
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        records: List[TargetApplicationRecord] = []
        for row in cursor.fetchall():
            records.append(
                TargetApplicationRecord(
                    vars_host_id=int(row["vars_host_id"]),
                    vars_host_name=str(row["vars_host_name"] or ""),
                    host_ip=str(row["host_ip"] or "").strip(),
                    host_application_id=int(row["host_application_id"]),
                    area_id=None if row["area_id"] is None else int(row["area_id"]),
                    area_name=None if row["area_name"] is None else str(row["area_name"]).strip(),
                    application_type_id=int(row["application_type_id"]),
                    application_id=int(row["application_id"]),
                    application_family_id=(
                        None
                        if row["application_family_id"] is None
                        else int(row["application_family_id"])
                    ),
                    application_version=(
                        None if row["application_version"] is None else str(row["application_version"])
                    ),
                    target_credential_type_id=(
                        None
                        if row["target_credential_type_id"] is None
                        else int(row["target_credential_type_id"])
                    ),
                )
            )
        return records


def build_duplicate_ip_errors(
    source_hosts: Sequence[ActiveHost],
    target_hosts: Sequence[ActiveHost],
) -> Tuple[Dict[str, Any], ...]:
    errors: List[Dict[str, Any]] = []
    for system_name, hosts in (("source", source_hosts), ("target", target_hosts)):
        grouped: Dict[str, List[ActiveHost]] = {}
        for host in hosts:
            grouped.setdefault(host.host_ip, []).append(host)
        for host_ip, group in sorted(grouped.items()):
            if len(group) < 2:
                continue
            errors.append(
                {
                    "system": system_name,
                    "host_ip": host_ip,
                    "count": len(group),
                    "hosts": [
                        {
                            "host_id": host.host_id,
                            "host_name": host.host_name,
                        }
                        for host in group
                    ],
                }
            )
    return tuple(errors)


def build_host_ip_summary(
    source_hosts: Sequence[ActiveHost],
    target_hosts: Sequence[ActiveHost],
) -> Dict[str, Any]:
    target_by_ip = {host.host_ip: host for host in target_hosts}
    intersections = []
    for source_host in source_hosts:
        target_host = target_by_ip.get(source_host.host_ip)
        if target_host is None:
            continue
        intersections.append(
            {
                "ip": source_host.host_ip,
                "fap_host_id": source_host.host_id,
                "fap_host_name": source_host.host_name,
                "vars_hosts": [
                    {
                        "vars_host_id": target_host.host_id,
                        "vars_host_name": target_host.host_name,
                    }
                ],
            }
        )

    return {
        "source_enabled_hosts": len(source_hosts),
        "target_enabled_hosts": len(target_hosts),
        "intersection_count": len(intersections),
        "intersections": intersections,
    }


def is_area_allowed(area_name: Optional[str], allowed_area_names: Optional[Tuple[str, ...]]) -> bool:
    if allowed_area_names is None:
        return True
    if area_name is None:
        return False
    return area_name.strip() in allowed_area_names


def make_decision_row(
    source_host: ActiveHost,
    source_credential: Optional[CredentialRecord],
    target_application: TargetApplicationRecord,
    settings: SyncSettings,
) -> DecisionRow:
    excluded_type_ids = set(settings.exclude_credential_type_ids)

    if not is_area_allowed(target_application.area_name, settings.allowed_area_names):
        decision = "skip_area_not_allowed"
    elif source_credential is None:
        decision = "skip_source_credential_missing"
    elif source_credential.credential_type_id in excluded_type_ids:
        decision = "skip_source_credential_type_excluded"
    elif target_application.target_credential_type_id is None:
        decision = "skip_target_credential_missing"
    elif target_application.target_credential_type_id in excluded_type_ids:
        decision = "skip_target_credential_type_excluded"
    elif (
        settings.require_same_credential_type
        and source_credential.credential_type_id != target_application.target_credential_type_id
    ):
        decision = "skip_credential_type_mismatch"
    else:
        decision = "eligible_update"

    return DecisionRow(
        ip=source_host.host_ip,
        fap_host_id=source_host.host_id,
        fap_host_name=source_host.host_name,
        source_credential_type_id=(
            None if source_credential is None else source_credential.credential_type_id
        ),
        vars_host_id=target_application.vars_host_id,
        vars_host_name=target_application.vars_host_name,
        host_application_id=target_application.host_application_id,
        area_id=target_application.area_id,
        area_name=target_application.area_name,
        application_type_id=target_application.application_type_id,
        application_id=target_application.application_id,
        application_family_id=target_application.application_family_id,
        application_version=target_application.application_version,
        target_credential_type_id=target_application.target_credential_type_id,
        decision=decision,
        source_input_data=None if source_credential is None else source_credential.input_data,
    )


def build_sync_plan(
    source_hosts: Sequence[ActiveHost],
    source_credentials: Mapping[int, CredentialRecord],
    target_hosts: Sequence[ActiveHost],
    target_applications: Sequence[TargetApplicationRecord],
    settings: SyncSettings,
) -> SyncPlan:
    duplicate_ip_errors = build_duplicate_ip_errors(source_hosts, target_hosts)
    host_ip_summary = build_host_ip_summary(source_hosts, target_hosts)
    if duplicate_ip_errors:
        return SyncPlan(
            blocked=True,
            duplicate_ip_errors=duplicate_ip_errors,
            host_ip_summary=host_ip_summary,
            decision_rows=tuple(),
        )

    source_by_ip = {host.host_ip: host for host in source_hosts}
    decision_rows: List[DecisionRow] = []
    for target_application in target_applications:
        source_host = source_by_ip.get(target_application.host_ip)
        if source_host is None:
            continue
        source_credential = source_credentials.get(source_host.host_id)
        decision_rows.append(
            make_decision_row(
                source_host=source_host,
                source_credential=source_credential,
                target_application=target_application,
                settings=settings,
            )
        )

    return SyncPlan(
        blocked=False,
        duplicate_ip_errors=tuple(),
        host_ip_summary=host_ip_summary,
        decision_rows=tuple(decision_rows),
    )


def serialize_decision_row(row: DecisionRow) -> Dict[str, Any]:
    return {
        "ip": row.ip,
        "fap_host_id": row.fap_host_id,
        "fap_host_name": row.fap_host_name,
        "source_credential_type_id": row.source_credential_type_id,
        "vars_host_id": row.vars_host_id,
        "vars_host_name": row.vars_host_name,
        "host_application_id": row.host_application_id,
        "area_id": row.area_id,
        "area_name": row.area_name,
        "application_type_id": row.application_type_id,
        "application_id": row.application_id,
        "application_family_id": row.application_family_id,
        "application_version": row.application_version,
        "target_credential_type_id": row.target_credential_type_id,
        "decision": row.decision,
    }


def build_report_payload(
    plan: SyncPlan,
    settings: SyncSettings,
    mode: str,
    applied_updates: int,
) -> Dict[str, Any]:
    updates = [serialize_decision_row(row) for row in plan.eligible_updates]
    skipped = [serialize_decision_row(row) for row in plan.decision_rows if row.decision != "eligible_update"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "blocked": plan.blocked,
        "settings": {
            "exclude_credential_type_ids": list(settings.exclude_credential_type_ids),
            "require_same_credential_type": settings.require_same_credential_type,
            "allowed_area_names": (
                None if settings.allowed_area_names is None else list(settings.allowed_area_names)
            ),
        },
        "host_ip_summary": plan.host_ip_summary,
        "decision_counts": plan.decision_counts,
        "matched_hai_rows": plan.decision_counts.get("matched_hai_rows", 0),
        "eligible_updates": len(plan.eligible_updates),
        "applied_updates": applied_updates,
        "duplicate_ip_errors": list(plan.duplicate_ip_errors),
        "updates": updates,
        "skipped": skipped,
    }


def write_report(report_path: Path, payload: Mapping[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def apply_updates(
    connection: psycopg.Connection[Any],
    updates: Sequence[DecisionRow],
    modified_by: Optional[int],
) -> int:
    if not updates:
        return 0

    if modified_by is None:
        sql = """
            update credential_host_application_info
               set input_data = %s,
                   modified_at = now()
             where host_application_id = %s
        """
    else:
        sql = """
            update credential_host_application_info
               set input_data = %s,
                   modified_by = %s,
                   modified_at = now()
             where host_application_id = %s
        """

    applied_updates = 0
    with connection.cursor() as cursor:
        for update in updates:
            if update.source_input_data is None:
                raise RuntimeError(
                    f"Eligible update {update.host_application_id} is missing source input_data"
                )

            if modified_by is None:
                params = (update.source_input_data, update.host_application_id)
            else:
                params = (update.source_input_data, modified_by, update.host_application_id)
            cursor.execute(sql, params)
            if cursor.rowcount != 1:
                raise RuntimeError(
                    f"Expected to update exactly one row for host_application_id "
                    f"{update.host_application_id}, got {cursor.rowcount}"
                )
            applied_updates += 1
    return applied_updates


def print_summary(summary: SyncSummary) -> None:
    print(f"mode: {summary.mode}")
    print(f"report: {summary.report_path}")
    print(f"blocked: {'yes' if summary.blocked else 'no'}")
    print(f"matched_hai_rows: {summary.matched_hai_rows}")
    print(f"eligible_updates: {summary.eligible_updates}")
    print(f"applied_updates: {summary.applied_updates}")
    for key in sorted(summary.decision_counts):
        print(f"{key}: {summary.decision_counts[key]}")
    if summary.duplicate_ip_errors:
        print(f"duplicate_ip_errors: {len(summary.duplicate_ip_errors)}")


def run_sync_from_config(config_path: Path, apply_changes: bool) -> SyncSummary:
    config = parse_config(config_path)
    mode = "apply" if apply_changes else "dry-run"

    with connect_database(config.source_db) as source_connection, connect_database(
        config.target_db
    ) as target_connection:
        source_hosts = fetch_active_hosts(source_connection)
        source_credentials = fetch_source_credentials(source_connection)
        target_hosts = fetch_active_hosts(target_connection)
        target_applications = fetch_target_applications(target_connection)
        plan = build_sync_plan(
            source_hosts=source_hosts,
            source_credentials=source_credentials,
            target_hosts=target_hosts,
            target_applications=target_applications,
            settings=config.sync,
        )
        applied_updates = 0
        if apply_changes and not plan.blocked:
            applied_updates = apply_updates(
                target_connection,
                plan.eligible_updates,
                config.sync.modified_by,
            )

    payload = build_report_payload(plan, config.sync, mode, applied_updates)
    write_report(config.sync.report_path, payload)

    return SyncSummary(
        report_path=config.sync.report_path,
        mode=mode,
        blocked=plan.blocked,
        matched_hai_rows=payload["matched_hai_rows"],
        eligible_updates=payload["eligible_updates"],
        applied_updates=applied_updates,
        decision_counts=plan.decision_counts,
        duplicate_ip_errors=plan.duplicate_ip_errors,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        summary = run_sync_from_config(Path(args.config), args.apply)
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_summary(summary)
    if summary.blocked:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
