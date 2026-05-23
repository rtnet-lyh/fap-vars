# Replay CLI Guide

`replay_cli.py`는 점검 케이스를 로컬에서 재생하거나 실제 장비에 접속해 실행하는 도구다. 보통은 실제 서버나 장비 없이 `replay.json`에 적어 둔 명령 결과를 사용해 `script.py` 로직을 검증한다.

## 한눈에 보기

현재 번들의 주요 구조는 다음과 같다.

```text
inspection_cases_bundle/
├── inspection_cases/
│   ├── server/
│   │   ├── rocky/
│   │   ├── windows/
│   │   ├── solaris/
│   │   ├── hpux/
│   │   └── esxi/
│   ├── network/
│   │   ├── cisco_ios/
│   │   └── nx_os/
│   ├── was/
│   ├── web/
│   └── tutorial/
└── inspection_runtime/
    ├── replay_cli.py
    ├── runner.py
    └── REPLAY_CLI_GUIDE.md
```

각 점검 케이스 디렉터리는 보통 아래 파일을 가진다.

```text
rocky_memory_usage_free_check/
├── case.json
├── script.py
├── replay.json
├── result.json
└── outputs/
```

- `case.json`: 점검 입력값, credential, threshold, item 정보
- `script.py`: 실제 점검 로직
- `replay.json`: `script.py`가 실행할 명령과 그 명령의 가짜 응답
- `outputs/*`: 긴 stdout을 따로 저장하는 파일
- `result.json`: CLI 실행 후 생성되는 결과
- `summary.json`: 디렉터리 단위 실행 후 생성되는 요약

## 런타임 파일 역할

대부분의 점검 추가/수정은 각 케이스 디렉터리의 `script.py`, `case.json`, `replay.json`, `outputs/*` 안에서 끝난다. 다만 여러 케이스가 같이 쓰는 기능이 부족하거나 실행 방식 자체가 바뀌어야 하면 `inspection_runtime/`의 공통 파일도 수정 대상이 될 수 있다.

| 파일 | 역할 | 주로 수정하는 경우 |
| --- | --- | --- |
| `inspection_runtime/replay_cli.py` | CLI 진입점. 케이스 디렉터리 탐색, replay/live 모드 선택, `result.json`과 `summary.json` 저장을 담당한다. | CLI 옵션, summary 형식, replay fixture 소비 방식이 바뀔 때 |
| `inspection_runtime/runner.py` | 실제 점검 payload 실행 엔진. `case.json`과 `script.py`를 실행 컨텍스트로 묶고 SSH, WinRM, no-ssh/API 실행 경로를 연결한다. | 접속 방식, credential 해석, item 실행 순서, 결과 포맷 공통 처리가 바뀔 때 |
| `inspection_runtime/items/common/_base.py` | 모든 `script.py`가 상속하는 `BaseCheck` 정의. `_ssh`, `_run_ps`, `_run_paramiko_commands`, threshold 조회, 결과 생성(`ok`, `fail`, `warn`) 같은 공통 API를 제공한다. | 여러 케이스에서 반복되는 공통 메서드가 필요하거나 Paramiko/threshold/result helper 동작을 확장할 때 |
| `inspection_runtime/items/common/helpers/network.py` | 네트워크 장비 설정 조회, section 추출, 라인 검색 같은 네트워크 점검 보조 함수 모음이다. | Cisco IOS, NX-OS 등 네트워크 케이스가 공통으로 쓸 파서나 조회 helper가 필요할 때 |
| `inspection_runtime/items/common/helpers/web.py` | URL 조합, HTTP 요청, cookie/session 관련 보조 함수 모음이다. | WebtoB, WAS, 웹 서비스 점검에서 공통 HTTP 처리나 인증 흐름이 필요할 때 |
| `inspection_runtime/items/common/helpers/vmware.py` | pyVmomi 기반 VMware/ESXi API 접속, inventory 조회, summary 직렬화 helper다. | ESXi/vCenter 계열 API 점검의 공통 조회 범위가 늘어날 때 |
| `inspection_runtime/items/common/helpers/__init__.py` | helper 클래스를 `NetworkHelper`, `WebHelper`, `VMwareHelper` 이름으로 export한다. | helper 모듈을 새로 추가하거나 export 이름을 바꿀 때 |
| `inspection_runtime/test_replay_cli.py` | `replay_cli.py` 동작 테스트다. | CLI, replay fixture, live 모드 처리 방식을 바꿀 때 |
| `inspection_runtime/test_runner.py` | `runner.py`와 실행 컨텍스트 동작 테스트다. | runner, credential, SSH/WinRM/API 실행 공통 로직을 바꿀 때 |

`script.py` 안에서는 `BaseCheck`가 붙여 준 `self.network_helper`, `self.web_helper`, `self.vmware_helper`로 helper를 사용할 수 있다.

## 실행 모드

`replay_cli.py`는 두 가지 모드를 지원한다.

| 모드 | 용도 | 읽는 파일 | 실제 접속 |
| --- | --- | --- | --- |
| `replay` | 로컬 fixture로 점검 로직 검증 | `case.json`, `script.py`, `replay.json` | 없음 |
| `live` | 실제 서버/장비 접속 실행 | `case.json`, `script.py` | 있음 |

기본값은 `replay` 모드다.

## 가장 많이 쓰는 명령

저장소 루트(`fap-vars/`)에서 실행할 때:

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py \
  inspection_cases_bundle/inspection_cases/server/rocky/rocky_memory_usage_free_check
```

번들 루트(`inspection_cases_bundle/`)로 이동해서 실행할 때:

```bash
python3 inspection_runtime/replay_cli.py \
  inspection_cases/server/rocky/rocky_memory_usage_free_check
```

Rocky 전체 케이스를 실행할 때:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/server/rocky
```

전체 케이스를 실행할 때:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases
```

실제 접속으로 단일 케이스를 실행할 때:

```bash
python3 inspection_runtime/replay_cli.py --mode live \
  inspection_cases/server/rocky/rocky_memory_usage_free_check
```

## 실행하면 어떤 파일이 바뀌나

단일 케이스 디렉터리를 실행하면 해당 케이스의 `result.json`만 갱신된다.

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/server/rocky/rocky_memory_usage_free_check
```

여러 케이스가 들어 있는 디렉터리를 실행하면 하위 케이스의 `result.json`과 실행한 디렉터리의 `summary.json`이 갱신된다.

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/server/rocky
```

전체 `inspection_cases`를 실행하면 여러 하위 케이스의 `result.json`과 최상위 `inspection_cases/summary.json`이 갱신된다.

```bash
python3 inspection_runtime/replay_cli.py inspection_cases
```

`result.json`에는 줄바꿈이 많은 값이 읽기 쉽도록 `raw_output_lines`, `check_script_lines`, `stdout_lines` 같은 보조 필드가 함께 들어갈 수 있다.

## Replay 모드 작동 방식

replay 모드는 실제 SSH, WinRM, Paramiko, API 호출 대신 `replay.json`을 순서대로 소비한다.

흐름은 단순하다.

1. CLI가 `case.json`을 읽는다.
2. CLI가 `script.py` 내용을 `case.json`의 item에 붙인다.
3. `script.py`가 `_ssh(...)`, `_run_ps(...)`, `_run_paramiko_commands(...)` 같은 메서드로 명령을 실행한다.
4. CLI가 실제 접속 대신 `replay.json`에서 다음 응답을 찾아 반환한다.
5. 실행 결과를 `result.json`에 쓴다.

`replay.json`의 순서와 `script.py`의 명령 실행 순서가 다르면 `REPLAY_MISS` 오류가 난다.

## 기본 `replay.json` 작성법

SSH, WinRM처럼 한 명령을 실행하고 결과를 받는 케이스는 아래 형태를 쓴다.

```json
[
  {
    "matcher_type": "exact",
    "matcher_value": "free -m",
    "rc": 0,
    "stdout_file": "outputs/free.stdout",
    "stderr": ""
  }
]
```

주요 필드:

- `matcher_type`: `exact`, `contains`, `regex` 중 하나
- `matcher_value`: `script.py`에서 실행하는 명령 문자열
- `rc`: 명령 종료 코드
- `stdout`: 짧은 표준 출력
- `stdout_file`: 긴 표준 출력 파일 경로
- `stderr`: 표준 에러
- `stderr_file`: 긴 표준 에러 파일 경로

권장 기준:

- 가능하면 `matcher_type`은 `exact`를 쓴다.
- `matcher_value`는 `_ssh("...")` 또는 `_run_ps("...")` 안의 문자열과 완전히 같게 쓴다.
- 긴 출력은 `stdout`에 직접 넣지 말고 `outputs/*.stdout` 파일로 분리한다.

## 여러 명령을 실행하는 케이스

`script.py`가 여러 명령을 실행하면 `replay.json`도 같은 순서로 적는다.

```json
[
  {
    "matcher_type": "exact",
    "matcher_value": "uname -a",
    "rc": 0,
    "stdout": "Linux host01 5.14.0\n",
    "stderr": ""
  },
  {
    "matcher_type": "exact",
    "matcher_value": "free -m",
    "rc": 0,
    "stdout_file": "outputs/free.stdout",
    "stderr": ""
  }
]
```

## Paramiko 대화형 케이스

네트워크 장비처럼 대화형 shell을 쓰는 케이스는 `channel: terminal` 규칙을 사용할 수 있다.

```json
[
  {
    "channel": "terminal",
    "action": "recv",
    "stdout": "Router>"
  },
  {
    "channel": "terminal",
    "action": "send",
    "matcher_value": "enable"
  },
  {
    "channel": "terminal",
    "action": "recv",
    "stdout": "Password:"
  },
  {
    "channel": "terminal",
    "action": "send",
    "redacted": true
  },
  {
    "channel": "terminal",
    "action": "recv",
    "stdout": "Router#"
  },
  {
    "channel": "terminal",
    "action": "send",
    "matcher_value": "show version"
  },
  {
    "channel": "terminal",
    "action": "recv",
    "stdout_file": "outputs/show_version.stdout"
  }
]
```

`action` 의미:

- `recv`: 장비가 보낸 문자열
- `send`: 스크립트가 보낸 입력
- `open`: shell을 열자마자 미리 받을 문자열이 있을 때 사용
- `close`: 세션 종료를 명시하고 싶을 때 사용

비밀번호처럼 결과 파일에 남기면 안 되는 값은 `redacted: true`를 쓴다. 이 경우 실제 입력값을 `matcher_value`에 적지 않는다.

## Live 모드

live 모드는 `replay.json`을 읽지 않고 실제 접속을 시도한다. 단일 케이스 디렉터리만 실행할 수 있다.

```bash
python3 inspection_runtime/replay_cli.py --mode live \
  inspection_cases/server/rocky/rocky_memory_usage_free_check
```

필수 조건:

- `case.json`에 `host`가 있어야 한다.
- `case.json`에 `user`가 있거나 `credentials`에 접속 계정이 있어야 한다.
- SSH 비밀번호 인증에는 환경에 따라 `sshpass`가 필요할 수 있다.
- Windows WinRM 케이스에는 `pywinrm`이 필요하다.
- ESXi API 케이스에는 `pyVmomi`가 필요하다.

주의할 점:

- live 모드는 실제 서버/장비 상태에 따라 결과가 달라진다.
- live 모드는 단일 케이스만 지원한다. `inspection_cases/server/rocky` 같은 묶음 경로로 실행하면 실패한다.
- `script.py`에 문법 오류나 import 오류가 있으면 Python 예외 원문이 `result.json`의 `message`, `raw_output`에 남는다.
- 운영 credential이 들어간 `case.json`은 커밋하지 않는다.

## 결과 확인 방법

단일 케이스 실행 후에는 `result.json`에서 다음 값을 먼저 본다.

- `failed_items`: 비어 있으면 보통 성공이다.
- `results[].status`: `ok`, `fail`, `warn`, `not_applicable` 등 케이스 판정 상태
- `results[].message`: 사람이 읽는 요약
- `results[].metrics`: 판정 근거 값
- `results[].thresholds`: 실제 적용 기준
- `results[].raw_output`: 디버깅용 원문 출력

디렉터리 단위 실행 후에는 `summary.json`에서 다음 값을 본다.

- `total_cases`: 실행한 케이스 수
- `failed_cases`: 실패한 케이스 목록
- `cases[].result_file`: 각 케이스의 결과 파일 경로

## 자주 나는 오류

### `case path not found`

입력한 경로가 존재하지 않는다. 현재 작업 디렉터리가 `fap-vars/`인지 `inspection_cases_bundle/`인지 확인하고 경로를 다시 맞춘다.

### `no case directories found under`

지정한 디렉터리 아래에 `case.json`, `script.py`, `replay.json`을 모두 가진 케이스 디렉터리가 없다.

### `REPLAY_MISS: expected ... but got ...`

`script.py`가 실행한 명령과 `replay.json`의 다음 규칙이 맞지 않는다.

확인할 것:

- 명령 문자열이 완전히 같은가
- `replay.json` 순서가 `script.py` 실행 순서와 같은가
- Paramiko terminal fixture에서 `send`와 `recv` 순서가 실제 흐름과 같은가

### `live mode requires a single case directory`

live 모드는 여러 케이스 디렉터리를 한 번에 실행할 수 없다. 정확한 케이스 디렉터리를 지정한다.

### `live mode requires host in case.json`

live 실행에 필요한 `host` 값이 `case.json`에 없다.

## 런타임과 헬퍼를 수정해야 하는 경우

기본 판단은 간단하다. 한 케이스에만 필요한 로직이면 해당 케이스의 `script.py`에 둔다. 같은 로직이 여러 케이스에서 반복되거나, 기존 공통 API로 표현하기 어려운 실행 흐름이면 `runner.py`, `_base.py`, helper 모듈 수정을 검토한다.

수정이 필요한 예:

- 여러 네트워크 케이스가 같은 설정 section 파서를 반복해서 쓰는 경우: `helpers/network.py`
- 여러 웹/WAS 케이스가 같은 로그인, cookie, HTTP 요청 흐름을 공유해야 하는 경우: `helpers/web.py`
- ESXi/vCenter API에서 공통 inventory 조회나 직렬화가 필요한 경우: `helpers/vmware.py`
- 모든 `script.py`에서 쓸 새 결과 helper, threshold helper, Paramiko helper가 필요한 경우: `_base.py`
- SSH/WinRM credential 해석, live 실행 방식, item payload 조립 방식이 바뀌는 경우: `runner.py`
- replay fixture 문법, CLI 옵션, summary 저장 방식이 바뀌는 경우: `replay_cli.py`

수정할 때 지킬 점:

- 공통 런타임 변경은 여러 케이스에 영향을 줄 수 있으므로 가장 작은 범위로 바꾼다.
- `_base.py`에 helper를 추가하면 기존 `script.py` API와 충돌하지 않는 이름을 쓴다.
- `runner.py`나 `replay_cli.py`를 바꾸면 관련 테스트도 같이 갱신한다.
- replay 케이스만 추가한 작업에서는 런타임을 먼저 바꾸지 말고 기존 API로 해결 가능한지 확인한다.

권장 검증은 저장소 루트(`fap-vars/`)에서 실행한다.

```bash
python3 -m unittest inspection_cases_bundle.inspection_runtime.test_replay_cli
python3 -m unittest inspection_cases_bundle.inspection_runtime.test_runner
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py inspection_cases_bundle/inspection_cases/tutorial
```

## 새 케이스를 만들 때 체크리스트

- `case.json`, `script.py`, `replay.json`이 모두 있는가
- `script.py`의 명령과 `replay.json.matcher_value`가 일치하는가
- 긴 stdout은 `outputs/*.stdout`로 분리했는가
- threshold 이름이 `case.json`과 `script.py`에서 같은가
- 단일 케이스 replay로 `result.json`을 갱신했는가
- 여러 케이스를 수정했다면 관련 `summary.json`도 갱신했는가

## 관련 문서

- `inspection_cases_bundle/AGENTS.md`: replay 케이스 작성 규칙
- `inspection_cases_bundle/raw_data/AGENTS.md`: 원천 Markdown 작성 규칙
- `inspection_cases_bundle/inspection_cases/README.md`: 케이스 구조와 작성 가이드
- `inspection_cases_bundle/inspection_cases/tutorial/README.md`: SSH, WinRM, Paramiko 튜토리얼
