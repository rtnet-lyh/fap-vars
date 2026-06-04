# Repository Guidelines

## 적용 범위와 상위 규칙

이 문서는 `inspection_cases_bundle/` 전체에 적용된다. 저장소 루트의 `AGENTS.md` 규칙도 함께 적용하며, 이 디렉터리 안에서는 이 문서의 replay 번들 규칙을 우선한다. `raw_data/` 아래에서는 `inspection_cases_bundle/raw_data/AGENTS.md`의 원천 Markdown 규칙이 가장 우선한다.

이 번들은 다른 OS에서도 바로 재생 가능한 점검 replay 케이스 모음이다. 기본 목표는 현재 구조를 유지한 채 새 점검 케이스를 빠르게 추가하거나 기존 케이스를 안전하게 수정하는 것이다.

## 프로젝트 구조 및 모듈 구성

- `inspection_cases/`: 점검 케이스 모음. 현재 주요 분류는 `server/`, `network/`, `was/`, `web/`, `storage/`, `dbms/`, `backup/`, `tutorial/`이다.
- `inspection_cases/server/`: `rocky`, `windows`, `solaris`, `hpux`, `esxi` 서버 계열 케이스를 둔다.
- `inspection_cases/network/`: `cisco_ios`, `nx_os`, `juniper_junos`, `piolink_pas` 등 네트워크 장비 케이스를 둔다.
- `inspection_cases/was/`와 `inspection_cases/web/`: JEUS, WebtoB처럼 애플리케이션 계열 점검 케이스를 둔다.
- `inspection_cases/storage/`: Dell DDOS 등 스토리지 장비 케이스를 둔다.
- `inspection_cases/dbms/`: Oracle 등 DBMS 계열 점검 케이스를 둔다.
- `inspection_cases/backup/`: NetBackup Appliance 등 백업 장비 또는 백업 솔루션 케이스를 둔다.
- `inspection_cases/tutorial/`: SSH, WinRM, Paramiko 작성 패턴을 확인하는 튜토리얼 케이스를 둔다.
- `inspection_runtime/`: replay/live 실행 최소 런타임이다. 일반 케이스 추가 작업에서는 수정하지 않는다.
- `raw_data/`: 점검 명령어, 출력 결과, 판단 근거를 담은 원천 Markdown 자료다.
- `api_data/`: API 문서화 또는 변환 산출물 성격의 Markdown 자료다. 명시 요청이 없으면 불필요하게 갱신하지 않는다.

새 점검 로직의 기본 위치는 `inspection_cases/<domain>/<platform_or_product>/<case_name>/`이다. 예: `inspection_cases/server/rocky/rocky_memory_usage_free_check/`, `inspection_cases/network/nx_os/mds_c9148s/1_1_cpu_check/`, `inspection_cases/backup/netbackup_appliance_5240/nbu_1_1_catalog_backup_status_check/`. 기존에 장비 모델, 제품, OS 하위 디렉터리가 있으면 가장 가까운 구조를 따른다.

## 빌드, 테스트, 개발 명령

저장소 루트(`fap-vars/`)에서 실행할 때:

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py inspection_cases_bundle/inspection_cases/server/rocky/rocky_memory_usage_free_check
```

번들 루트(`inspection_cases_bundle/`)에서 실행할 때:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/server/rocky/rocky_memory_usage_free_check
```

분류 단위 또는 전체 재생:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/server/rocky
python3 inspection_runtime/replay_cli.py inspection_cases
```

실제 접속 기반 live 실행은 단일 케이스만 지원하며, 사용자가 명시적으로 요청한 경우에만 실행한다.

```bash
python3 inspection_runtime/replay_cli.py --mode live inspection_cases/server/rocky/rocky_memory_usage_free_check
```

## 기본 원칙

- 사용자가 "스크립트 만들어줘"라고만 말해도 이 번들에서는 standalone shell보다 replay 케이스를 우선 고려한다.
- standalone shell 스크립트는 사용자가 명시적으로 원할 때만 추가한다.
- replay 케이스는 기존 케이스와 같은 파일 세트와 디렉터리 구조를 맞춘다.
- `result.json`, `summary.json`은 생성 산출물이므로 가능하면 수동 편집하지 말고 replay 실행으로 갱신한다.
- 긴 명령 출력은 `replay.json`의 `stdout`에 직접 넣지 말고 `outputs/*.stdout` 파일로 분리한다.
- 임계치를 쓰는 경우 `case.json`의 `item.threshold_list[].name`과 `script.py`의 `get_threshold_var(...)` 키를 반드시 동일하게 맞춘다.
- `replay.json`의 `matcher_value`는 `script.py`가 실제 실행하는 명령 문자열과 동일해야 한다.
- `script.py`와 특정 케이스 파일을 제외한 `inspection_runtime/` helper, common, runner 수정은 피한다.

## 케이스 디렉터리 표준 구성

각 케이스는 보통 아래 구조를 따른다.

```text
inspection_cases/<domain>/<platform>/<case_name>/
├── case.json
├── replay.json
├── result.json
├── script.py
└── outputs/
```

`outputs/`는 긴 stdout이 없으면 생략 가능하지만, 일반적으로 만드는 편이 안전하다. 일부 기존 Windows, Solaris, Backup 케이스에는 호환용 `raw_data.md`가 있을 수 있으나, 새 Rocky 계열 케이스는 `raw_data/server/rocky/*.md`를 정본으로 본다.

## OS 및 연결 방식별 작성 규칙

### Linux, Rocky, Unix 계열

- `script.py`에서 `USE_HOST_CONNECTION = True`를 사용한다.
- 일반 SSH 명령은 `CONNECTION_METHOD = 'ssh'`와 `_ssh("...")` 패턴을 사용한다.
- 연결 실패는 `self._is_connection_error(rc, err)`로 먼저 처리한다.
- 일반 명령 실패는 `rc != 0` 분기에서 별도 메시지로 처리한다.

### Network 장비

- SSH exec 채널로 충분한 장비는 `_ssh("...")` 패턴을 사용한다.
- 대화형 세션, enable mode, pager 제어가 필요한 장비는 `CONNECTION_METHOD = 'paramiko'`와 `_run_paramiko_commands([...])` 패턴을 우선 검토한다.
- Paramiko 옵션은 credential `data`에 넣지 말고 `PARAMIKO_*` 클래스 속성으로 조정한다.
- `hide_command`가 필요한 입력은 dict 항목으로 넘겨 raw output과 command history에 실제 명령이 남지 않게 한다.

### Windows

- `CONNECTION_METHOD = 'winrm'`를 사용한다.
- 필요 시 `WINRM_SHELL = 'powershell'`를 둔다.
- 명령 실행은 `_run_ps("...")` 패턴을 사용한다.
- WinRM 환경 자체가 없을 수 있으므로 `self._is_not_applicable(rc, err)` 분기를 고려한다.

### ESXi 및 API 기반 케이스

- 장비 접속 명령보다 API 또는 replay payload 평가가 핵심이면 `USE_HOST_CONNECTION = False` 패턴을 따른다.
- live 실행 가능 여부와 필요한 credential 형식은 가까운 `server/esxi/*/script.py` 케이스를 기준으로 맞춘다.

## `script.py` 작성 규칙

`script.py`는 `BaseCheck`를 상속하는 Python 스크립트여야 한다. 작성 시 반드시 연결 실패, 명령 실패, 파싱 실패, 정책 실패를 구분해서 반환한다.

정상 반환에는 가능한 한 다음 값을 채운다.

- `metrics`: 판정 근거가 되는 측정값
- `thresholds`: 실제 적용된 기준값
- `reasons`: 판정 사유
- `message`: 사람이 결과를 읽었을 때 바로 이해할 수 있는 요약

Python 코드는 루트 규칙과 같이 공백 4칸 들여쓰기, 표준 라이브러리 우선 import, `snake_case` 이름을 사용한다.

## `case.json` 작성 규칙

- `inspection_code`는 케이스별로 유일해야 한다.
- 실제 핵심은 `credentials`, `item`, `item.threshold_list`이다.
- `host`, `port`, `execution_id`, `host_id`, `job_id`, `item_id` 같은 메타 필드는 replay용 placeholder여도 된다.
- 새 케이스는 가장 가까운 기존 케이스 또는 `inspection_cases/tutorial/`의 starter 패턴을 기준으로 시작한다.
- threshold가 없는 케이스는 `threshold_list`를 빈 배열로 둔다.

## `replay.json` 작성 규칙

- 배열 형태로 유지한다.
- 각 엔트리의 `matcher_type`은 특별한 이유가 없으면 `exact`를 사용한다.
- `matcher_value`는 실제 실행 명령과 완전히 같아야 한다.
- 짧은 출력은 `stdout`, 긴 출력은 `stdout_file`을 사용한다.
- 여러 명령을 실행하면 스크립트 호출 순서대로 엔트리를 나열한다.

예시:

```json
[
  {
    "matcher_type": "exact",
    "matcher_value": "df -h",
    "rc": 0,
    "stdout_file": "outputs/df.stdout",
    "stderr": ""
  }
]
```

## Codex 작업 절차

새 점검 요청을 받으면 아래 순서로 처리한다.

1. 가장 가까운 기존 케이스 또는 `tutorial/` starter를 찾는다.
2. 새 디렉터리를 `inspection_cases/<domain>/<platform>/<case_name>/`으로 만든다.
3. `case.json`을 기준 케이스 기반으로 작성하고 필요한 threshold를 넣는다.
4. `script.py`를 작성한다.
5. `replay.json`과 필요 시 `outputs/*`를 작성한다.
6. 단일 케이스 replay를 실행한다.
7. 생성된 `result.json`의 status, metrics, thresholds, message를 확인한다.
8. 여러 케이스를 건드렸으면 관련 분류 또는 전체 `summary.json`도 replay 실행으로 갱신한다.

## 검증 지침

최소 확인 포인트:

- `result.json.results[].status`가 기대와 같은지
- `failed_items`가 의도와 같은지
- `metrics`에 판정 근거가 충분한지
- `thresholds`에 실제 적용값이 남았는지
- `message`, `reasons`, `raw_output`이 디버깅 가능한 수준인지
- `summary.json.failed_cases`가 케이스별 `result.json`과 모순되지 않는지

문서만 수정한 경우 자동 테스트는 필수가 아니지만, 실행하지 않은 검증은 최종 응답에 명확히 적는다.

## 수정 범위 제한

다음 경우가 아니면 `inspection_runtime/` 수정은 피한다.

- 런타임 버그 때문에 어떤 케이스도 정상 재생되지 않는 경우
- 여러 케이스에 공통으로 필요한 helper 추가가 명확한 경우
- 사용자가 런타임 자체 수정까지 명시적으로 요청한 경우

새 점검 하나를 추가하는 작업이라면 우선 `inspection_cases/` 안에서 끝낸다. 원천 문서만 추가하는 작업이면 `raw_data/` 안에서 끝내고 replay 케이스를 새로 만들지 않는다.

## 커밋 및 PR 지침

루트 `AGENTS.md`의 커밋/PR 규칙을 따른다. PR에는 변경 범위가 runtime, replay case, raw data, api data 중 어디인지 명확히 적고, 실행한 replay 명령을 함께 남긴다. 생성 파일이나 케이스 rename이 포함되면 의도된 변경임을 설명한다.

## Agent 전용 지침

작업 전 `git status --short`로 기존 변경을 확인하고, 관련 없는 working tree 변경을 되돌리지 않는다. 운영 credential, live 접속, 대량 `summary.json` 재생성은 사용자의 요청 범위 안에서만 수행한다.
