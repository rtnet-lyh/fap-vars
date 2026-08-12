#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="${FAP_MANAGER_CONTAINER:-vars-manager}"
PYTHON_BIN="${FAP_MANAGER_PYTHON:-python3}"
CONFIG_PATH="${SCRIPT_DIR}/sample_config.yml"
REPORT_PATH="${SCRIPT_DIR}/sync_report.json"
APPLY_CHANGES=true
CONTAINER_WORK_DIR=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Run sync_credentials.py inside the vars-manager Docker container.
Dry-run is the default; use --apply only when target DB updates are intended.

Options:
  --config PATH      Host-side YAML config path
                     (default: ${CONFIG_PATH})
  --report PATH      Host-side JSON report output path
                     (default: ${REPORT_PATH})
  --container NAME   Docker container name
                     (default: ${CONTAINER_NAME})
  --apply            Apply eligible updates to the VARS DB
  -h, --help         Show this help

Environment variables:
  FAP_MANAGER_CONTAINER  Default container name
  FAP_MANAGER_PYTHON     Python executable inside the container
EOF
}

die() {
    echo "Error: $*" >&2
    exit 1
}

cleanup() {
    if [[ -n "${CONTAINER_WORK_DIR}" && "${CONTAINER_WORK_DIR}" == /tmp/fap_credential_sync.* ]]; then
        docker exec "${CONTAINER_NAME}" rm -rf -- "${CONTAINER_WORK_DIR}" >/dev/null 2>&1 || true
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)
            [[ $# -ge 2 ]] || die "--config requires a path"
            CONFIG_PATH="$2"
            shift 2
            ;;
        --report)
            [[ $# -ge 2 ]] || die "--report requires a path"
            REPORT_PATH="$2"
            shift 2
            ;;
        --container)
            [[ $# -ge 2 ]] || die "--container requires a name"
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --apply)
            APPLY_CHANGES=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1 (use --help for usage)"
            ;;
    esac
done

command -v docker >/dev/null 2>&1 || die "docker command was not found"
[[ -r "${SCRIPT_DIR}/sync_credentials.py" ]] || die "sync_credentials.py was not found in ${SCRIPT_DIR}"
[[ -r "${CONFIG_PATH}" ]] || die "config file is not readable: ${CONFIG_PATH}"

CONTAINER_RUNNING="$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
[[ "${CONTAINER_RUNNING}" == "true" ]] || die "container is not running: ${CONTAINER_NAME}"

docker exec "${CONTAINER_NAME}" "${PYTHON_BIN}" -c 'import psycopg, yaml' >/dev/null 2>&1 ||
    die "${PYTHON_BIN} or required modules (psycopg, PyYAML) are unavailable in ${CONTAINER_NAME}"

CONTAINER_WORK_DIR="$(
    docker exec "${CONTAINER_NAME}" mktemp -d /tmp/fap_credential_sync.XXXXXX
)"
[[ "${CONTAINER_WORK_DIR}" == /tmp/fap_credential_sync.* ]] ||
    die "unexpected container temporary directory: ${CONTAINER_WORK_DIR}"
trap cleanup EXIT

CONTAINER_SCRIPT="${CONTAINER_WORK_DIR}/sync_credentials.py"
CONTAINER_SOURCE_CONFIG="${CONTAINER_WORK_DIR}/source_config.yml"
CONTAINER_CONFIG="${CONTAINER_WORK_DIR}/config.yml"
CONTAINER_REPORT="${CONTAINER_WORK_DIR}/sync_report.json"

docker cp "${SCRIPT_DIR}/sync_credentials.py" "${CONTAINER_NAME}:${CONTAINER_SCRIPT}" >/dev/null
docker cp "${CONFIG_PATH}" "${CONTAINER_NAME}:${CONTAINER_SOURCE_CONFIG}" >/dev/null

# Use a temporary config so report_path is deterministic inside the container.
# The original host config is never modified.
docker exec "${CONTAINER_NAME}" "${PYTHON_BIN}" -c '
import pathlib
import sys

import yaml

source_path = pathlib.Path(sys.argv[1])
output_path = pathlib.Path(sys.argv[2])
report_path = sys.argv[3]
payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
if not isinstance(payload, dict):
    raise SystemExit("config root must be a YAML mapping")
sync = payload.setdefault("sync", {})
if not isinstance(sync, dict):
    raise SystemExit("sync must be a YAML mapping")
sync["report_path"] = report_path
output_path.write_text(
    yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
    encoding="utf-8",
)
' "${CONTAINER_SOURCE_CONFIG}" "${CONTAINER_CONFIG}" "${CONTAINER_REPORT}"

SYNC_ARGS=(--config "${CONTAINER_CONFIG}")
if [[ "${APPLY_CHANGES}" == "true" ]]; then
    SYNC_ARGS+=(--apply)
    echo "Running FAP -> VARS credential sync in APPLY mode (${CONTAINER_NAME})"
else
    echo "Running FAP -> VARS credential sync in DRY-RUN mode (${CONTAINER_NAME})"
fi

set +e
docker exec "${CONTAINER_NAME}" "${PYTHON_BIN}" "${CONTAINER_SCRIPT}" "${SYNC_ARGS[@]}"
SYNC_STATUS=$?
set -e

if docker exec "${CONTAINER_NAME}" test -f "${CONTAINER_REPORT}"; then
    mkdir -p -- "$(dirname -- "${REPORT_PATH}")"
    docker cp "${CONTAINER_NAME}:${CONTAINER_REPORT}" "${REPORT_PATH}" >/dev/null
    echo "Report copied to: ${REPORT_PATH}"
fi

exit "${SYNC_STATUS}"
