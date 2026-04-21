# Inspection Cases Guide

이 디렉터리는 점검 항목을 실제 장비에 접속하지 않고 재생 검증하기 위한 케이스 모음이다.
각 케이스는 입력값(`case.json`), 재생 응답(`replay.json`), 점검 로직(`script.py`), 실행 결과(`result.json`)를 함께 관리한다.

필요하면 동일한 케이스를 `replay_cli.py --mode live`로 실제 접속 기반 실행도 할 수 있다. live 기본값은 케이스의 `case.json`을 그대로 사용하고, 접속 정보나 threshold만 바꾸고 싶을 때만 별도 override JSON을 추가로 준다.

원천 설명 문서는 상위 `inspection_cases_bundle/raw_data/`에서 관리한다. Rocky 케이스 디렉터리에는 `raw_data.md` 사본을 두지 않고, 필요한 설명은 `raw_data/rocky/*.md`를 정본으로 본다.

## 디렉터리 구조

```text
inspection_cases/
├── server/
│   ├── rocky/
│   │   ├── rocky_cpu_core_check/
│   │   │   ├── case.json
│   │   │   ├── replay.json
│   │   │   ├── result.json
│   │   │   ├── script.py
│   │   │   └── outputs/
│   │   ├── rocky_memory_usage_free_check/
│   │   ├── rocky_disk_recognition_lsblk_check/
│   │   └── summary.json
│   └── windows/
│       ├── windows_cpu_core_cim_check/
│       ├── windows_memory_usage_cim_check/
│       └── ...
└── summary.json
```

Rocky Linux 케이스는 `server/rocky/rocky_<domain>_<detail>_<command>_check/` 형태를 우선 사용한다.
Windows 케이스는 `server/windows/windows_<domain>_<detail>_<command>_check/` 형태를 우선 사용한다.

## 파일 역할

| 파일 | 역할 | 확인 포인트 |
| --- | --- | --- |
| `case.json` | 점검 입력과 실행 컨텍스트 | `credentials`, `item`, `item.threshold_list`가 핵심 |
| `script.py` | 실제 점검 로직 | 실행 명령, 연결 실패, 명령 실패, 파싱 실패, 정책 실패 처리가 분리되어야 함 |
| `replay.json` | 명령 재생 응답 정의 | `matcher_value`가 `script.py`에서 실행하는 명령 문자열과 같아야 함 |
| `outputs/*` | 긴 stdout 저장 파일 | `replay.json`의 `stdout_file`과 상대 경로가 맞아야 함 |
| `result.json` | replay 실행 결과 | 수동 편집보다 `replay_cli.py` 실행 산출물로 갱신 |
| `summary.json` | 여러 케이스 집계 결과 | 전체 또는 OS별 replay 실행으로 갱신 |

`result.json`에는 실행 당시의 `check_script`, `check_script_lines`, `raw_output`, `raw_output_lines`가 포함될 수 있다. 이 값들은 검토용 산출물이므로 가능하면 직접 수정하지 않는다.

## 케이스 작성 규칙

새 케이스는 가장 가까운 기존 케이스를 기준으로 시작한다.

- Linux/Rocky 계열은 `CONNECTION_METHOD = 'ssh'`와 `_ssh("...")` 패턴을 사용한다.
- Windows 계열은 `CONNECTION_METHOD = 'winrm'`와 `_run_ps("...")` 패턴을 사용한다.
- 대화형 SSH 세션이 필요한 장비는 `_open_terminal(...)`로 PTY 세션을 열고 `terminal.py` helper를 우선 사용한다.
- 네트워크 장비는 `term.use_profile('cisco_ios')`, `term.use_profile('junos')`, `term.use_profile('generic_network')`처럼 profile을 적용한 뒤 `enter_privilege()`, `disable_paging()`, `run_command()`를 조합한다.
- Linux/Unix 계열에서 interactive `su`가 필요한 경우 `run_su_command()`를 우선 사용한다.
- `drain()`은 명령 결과 수집보다 배너/잡출력 비우기 용도에 가깝다. 실제 명령 결과는 `run_command()` 또는 `run_su_command()`를 우선 사용한다.
- 연결 실패는 `_is_connection_error(...)`로 먼저 분기한다.
- 명령 실행 실패와 출력 파싱 실패는 별도 실패 메시지로 구분한다.
- 정상 결과는 `metrics`, `thresholds`, `reasons`, `message`를 가능한 한 채운다.
- 임계치를 쓰는 경우 `case.json`의 `item.threshold_list[].name`과 `script.py`의 `get_threshold_var(...)` 키를 반드시 일치시킨다.
- 긴 명령 출력은 `replay.json`에 직접 넣지 말고 `outputs/*.stdout` 파일로 분리한다.

## Interactive Terminal Helper

`inspection_runtime/terminal.py`는 대화형 SSH 세션용 공통 helper를 제공한다.

- `term.use_profile('cisco_ios')`: Cisco IOS prompt/pager/enable 규칙 적용
- `term.use_profile('junos')`: Junos prompt/pager 규칙 적용
- `term.use_profile('generic_network')`: 프롬프트가 확실하지 않은 네트워크 장비용 기본 규칙 적용
- `term.use_profile({...})`: prompt/pager 규칙을 케이스에서 직접 override
- `term.enter_privilege(password=...)`: Cisco `enable` 같은 권한 상승 처리
- `term.disable_paging()`: profile에 정의된 paging 해제 명령 실행
- `term.run_command('show version', timeout_sec=30)`: prompt 기준으로 명령 결과 수집
- `term.run_su_command('cat /etc/passwd', password=..., timeout_sec=30)`: `su - <user> -c ...` 기준으로 명령 결과 수집
- `term.run_until_marker(...)`: shell 계열에서 marker 기준으로 결과 수집
- `term.expect(...)`, `term.sendline(...)`, `term.drain(...)`: 세밀한 제어가 필요할 때만 직접 사용

Cisco IOS 예시:

```python
with self._open_terminal() as term:
    term.use_profile('cisco_ios')
    privilege_escalation_used = term.enter_privilege(
        password=self.get_connection_value('en_password', ''),
    )
    term.disable_paging()
    result = term.run_command('show version', timeout_sec=30)
```

Linux `su` 예시:

```python
with self._open_terminal() as term:
    result = term.run_su_command(
        'cat /etc/passwd',
        password=self.get_connection_value('en_password', ''),
        timeout_sec=30,
    )
```

## `case.json`

`case.json`은 replay 실행에 필요한 입력과 placeholder 메타데이터를 담는다.

```json
{
  "host": "127.0.0.1",
  "port": 22,
  "credentials": {
    "LINUX": [
      {
        "credential_type_name": "SSH",
        "data": {
          "username": "root",
          "password": ""
        }
      }
    ]
  },
  "thresholds": {},
  "item_sleep_sec": 0,
  "execution_id": 1,
  "host_id": 10,
  "job_id": 100,
  "item": {
    "inspection_code": "U-REPLAY-EXAMPLE-01",
    "item_id": 90001,
    "application_type_name": "LINUX",
    "threshold_list": [
      {
        "name": "fail_keywords",
        "value1": "offline"
      }
    ]
  }
}
```

작성 시 확인할 값:

- `inspection_code`는 케이스별로 유일하게 둔다.
- `item_id`, `application_id`, `execution_id`, `host_id`, `job_id`는 replay용 placeholder여도 된다.
- SSH, WinRM, become 정보는 대상 OS와 스크립트 실행 방식에 맞게 둔다.
- threshold가 없는 케이스는 `threshold_list`를 빈 배열로 둔다.

## `replay.json`

`replay.json`은 스크립트가 실행하는 명령과 그 결과를 고정한다.

```json
[
  {
    "matcher_type": "exact",
    "matcher_value": "lscpu",
    "rc": 0,
    "stdout_file": "outputs/lscpu.stdout",
    "stderr": ""
  }
]
```

작성 시 확인할 값:

- `matcher_value`는 `script.py`의 실제 `_ssh(...)` 또는 `_run_ps(...)` 명령과 완전히 같아야 한다.
- 짧은 출력은 `stdout`, 긴 출력은 `stdout_file`을 사용한다.
- 실패 시나리오는 의도에 맞게 `rc`, `stdout`, `stderr`를 조정한다.
- 여러 명령을 실행하는 스크립트는 실행 순서대로 replay 엔트리를 나열한다.
- interactive terminal 케이스는 `channel: terminal` 이벤트를 순서대로 나열한다. `send`는 helper가 실제로 보낸 텍스트, `recv`는 장비가 반환한 prompt/출력을 의미한다.
- `run_command()`를 쓰는 경우 replay 마지막 `recv`에는 명령 출력과 종료 prompt가 함께 들어가야 한다.
- `enter_privilege()`를 쓰는 Cisco 케이스는 일반적으로 `recv('>') -> send('enable') -> recv('Password:') -> send(redacted) -> recv('#')` 순서를 가진다.
- `disable_paging()`를 쓰는 profile은 paging 해제 명령도 replay에 포함해야 한다.

## 실행 방법

번들 루트에서 단일 케이스를 실행한다.

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py \
  inspection_cases_bundle/inspection_cases/server/rocky/rocky_cpu_core_check
```

실제 접속 기반 live 실행은 단일 케이스만 지원한다.

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py \
  --mode live \
  inspection_cases_bundle/inspection_cases/server/rocky/rocky_cpu_core_check
```

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py \
  --mode live \
  --override-file inspection_cases_bundle/live_inputs/rocky_cpu_core_check.json \
  inspection_cases_bundle/inspection_cases/server/rocky/rocky_cpu_core_check
```

Rocky 전체 케이스를 실행한다.

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py \
  inspection_cases_bundle/inspection_cases/server/rocky
```

전체 케이스를 실행한다.

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py \
  inspection_cases_bundle/inspection_cases
```

실행 결과:

- 단일 케이스 실행: 해당 케이스의 `result.json` 갱신
- OS별 디렉터리 실행: 하위 케이스의 `result.json`과 OS별 `summary.json` 갱신
- 전체 디렉터리 실행: 모든 하위 결과와 최상위 `summary.json` 갱신
- live 단일 케이스 실행: 해당 케이스의 `result.json`만 갱신

## Live Override JSON

live override 파일은 선택 사항이며, 필요할 때만 `case.json`의 부분 object 형식으로 작성한다.

```json
{
  "host": "10.10.10.20",
  "credentials": {
    "LINUX": [
      {
        "application_type_name": "LINUX",
        "credential_type_name": "SSH",
        "data": {
          "username": "inspector",
          "password": "secret"
        }
      }
    ]
  },
  "item": {
    "threshold_list": [
      {
        "name": "max_cpu_usage_percent",
        "value1": "70"
      }
    ]
  }
}
```

규칙:

- dict는 원본 `case.json`과 재귀 병합된다.
- list는 전체 교체된다. 예를 들어 `item.threshold_list`를 일부만 추가하지 않고 새 목록으로 통째로 넣어야 한다.
- `host`는 필수다.
- `user`를 직접 주거나 `credentials`에 실제 접속용 계정을 넣어야 한다.
- replay 모드와 달리 `replay.json`은 읽지 않고 실제 SSH, WinRM, VMware API 경로를 탄다.
- live 모드에서 `script.py`에 문법 오류나 top-level import 오류가 있으면 `점검 스크립트 없음`이 아니라 Python 예외 원문이 그대로 결과 `message`와 `raw_output`에 기록된다.

## 결과 검증

최소 검증 포인트:

- `result.json.results[].status`가 기대 상태인지 확인한다.
- `result.json.failed_items`가 의도와 맞는지 확인한다.
- `metrics`에 판정 근거가 남아 있는지 확인한다.
- `thresholds`에 실제 적용된 기준값이 남아 있는지 확인한다.
- `message`, `reasons`, `raw_output`이 장애 분석에 충분한지 확인한다.
- `summary.json.failed_cases`가 케이스별 `result.json`과 모순되지 않는지 확인한다.

상태 값은 케이스 로직에 따라 `ok`, `fail`, `warn`, `not_applicable` 등을 사용할 수 있다.

## 원천 문서 관리

점검 설명 Markdown은 `inspection_cases_bundle/raw_data/`에서 관리한다.

```text
raw_data/
├── rocky/
│   ├── rocky_cpu_core_check.md
│   ├── rocky_cpu_usage_check.md
│   └── ...
└── windows/
    ├── windows_cpu_core_cim_check.md
    └── ...
```

원칙:

- Rocky 원천 문서는 `raw_data/rocky/*.md`를 정본으로 본다.
- Rocky replay 케이스 디렉터리에는 `raw_data.md` 사본을 두지 않는다.
- Windows 쪽에 남아 있는 `raw_data.md`는 호환용 사본일 수 있으므로 정리 범위를 명시적으로 확인하고 수정한다.
- 원천 문서만 추가하는 작업이면 `inspection_cases/`의 replay 파일을 만들지 않는다.
- replay 케이스를 추가하는 작업이면 `case.json`, `script.py`, `replay.json`, `outputs/*`, `result.json` 정합성을 함께 맞춘다.

## 운영 체크리스트

- 새 케이스 디렉터리 이름이 OS와 점검 목적을 드러내는가
- `case.json`의 threshold 이름과 `script.py`의 `get_threshold_var(...)` 이름이 일치하는가
- `replay.json.matcher_value`가 실제 실행 명령과 일치하는가
- 긴 stdout이 `outputs/*.stdout`로 분리되어 있는가
- `script.py`가 연결 실패, 명령 실패, 파싱 실패, 판정 실패를 구분하는가
- `result.json`이 replay 실행으로 갱신되었는가
- 여러 케이스를 변경했다면 관련 `summary.json`을 다시 생성했는가
- 관련 없는 working tree 변경을 되돌리지 않았는가
