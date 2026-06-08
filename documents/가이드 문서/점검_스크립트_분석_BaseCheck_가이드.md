# 점검 스크립트 분석과 BaseCheck 활용 가이드

이 문서는 하나의 점검 스크립트를 기준으로 `script.py`를 어떻게 읽고, 현장에서 `inspection_runtime/items/common/_base.py`까지 어떻게 따라가야 하는지 설명한다. 주요 대상 함수는 `_ssh`, `_run_paramiko_commands`, `_run_paramiko`, `get_threshold_var`, `ok`, `warn`, `fail`이다.

예제의 중심 스크립트는 아래 파일이다.

```text
inspection_cases_bundle/inspection_cases/server/rocky/rocky_memory_usage_free_check/script.py
```

Paramiko 흐름은 별도 보조 예제로 아래 파일을 함께 본다.

```text
inspection_cases_bundle/inspection_cases/tutorial/cisco_ios/cisco_ios_paramiko_01_show_clock_check/script.py
inspection_cases_bundle/inspection_cases/network/piolink_pas/pas_k3200x/pio_3_2_svc_mac_chk/script.py
```

## 0. script.py를 읽는 기본 순서

현장에서 점검 스크립트를 분석할 때는 위에서 아래로 읽되, 실제로는 다음 순서를 고정해 두면 빠르다.

1. 상단 상수에서 실제 실행 명령을 확인한다.
2. `class Check(BaseCheck)`의 연결 방식을 확인한다.
3. `run()` 안에서 threshold 조회부를 확인한다.
4. `_ssh(...)`, `_run_ps(...)`, `_run_paramiko_commands(...)` 같은 실행 함수를 확인한다.
5. 명령 실패, 파싱 실패, 정책 실패 분기를 확인한다.
6. 정상/경고/실패 반환이 `ok`, `warn`, `fail` 중 무엇인지 확인한다.
7. 화면에 보이는 반환값인 `metrics`, `message`가 충분한지 확인한다. `fail`은 `error`도 함께 확인한다.
8. 필요하면 `_base.py`에서 호출한 함수의 실제 구현을 따라간다.

`script.py`는 독립 실행 프로그램이 아니라 `replay_cli.py`와 `runner.py`가 실행 컨텍스트를 만들어 주는 점검 클래스다. 그래서 `BaseCheck`가 가진 `ctx`, 접속 함수, credential, threshold, 결과 포맷 helper를 이해해야 한다.

운영 runner 흐름에서는 `script.py`가 실행되기 전에 host precheck가 먼저 수행된다. 따라서 개별 점검 스크립트 안에서 `true`, `hostname`, `echo` 같은 별도 연결 상태체크 명령을 다시 넣을 필요는 없다. 스크립트 안의 `_is_connection_error(...)` 분기는 연결 precheck를 반복하는 용도가 아니라, 실제 점검 명령 실행 중 끊김, timeout, credential 변경, replay/live 단독 실행처럼 런타임에서 반환된 오류를 사람이 읽을 수 있게 분류하는 보조 처리로 이해하면 된다.

화면 표시 기준으로는 `ok`, `warn`은 `metrics`와 `message`만 잘 채우면 된다. `fail`은 여기에 `error` 값만 추가로 잘 잡으면 된다. 코드 인자명은 `message` 단수이며, 화면에서 “messages”처럼 보이더라도 스크립트에서는 `message=`를 사용한다.

## 1. 예제 스크립트 전체 구조

`rocky_memory_usage_free_check/script.py`의 핵심 구조는 다음과 같다.

```python
# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


FREE_COMMAND = 'free'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        min_available_memory_percent = self.get_threshold_var(
            'min_available_memory_percent',
            default=10.0,
            value_type='float',
        )
        max_swap_usage_percent = self.get_threshold_var(
            'max_swap_usage_percent',
            default=50.0,
            value_type='float',
        )
        rc, out, err = self._ssh(FREE_COMMAND)
        ...


CHECK_CLASS = Check
```

각 구성요소의 의미는 다음과 같다.

| 코드 | 의미 | 현장 확인 포인트 |
| --- | --- | --- |
| `from .common._base import BaseCheck` | 모든 점검 스크립트가 쓰는 공통 부모 클래스다. | 함수 동작이 궁금하면 `_base.py`를 본다. |
| `FREE_COMMAND = 'free'` | 실제 실행할 명령 문자열이다. | `replay.json.matcher_value`와 같아야 한다. |
| `class Check(BaseCheck)` | 점검 클래스 정의다. | `CHECK_CLASS = Check`가 파일 하단에 있어야 runner가 찾는다. |
| `USE_HOST_CONNECTION = True` | 대상 호스트 접속이 필요하다는 뜻이다. | API/replay payload 평가만 하는 케이스는 `False`일 수 있다. |
| `CONNECTION_METHOD = 'ssh'` | SSH 실행 경로를 사용한다. | `paramiko`, `winrm`이면 실행 helper와 credential 선택 방식이 달라진다. |
| `run(self)` | 점검의 진입점이다. | 이 함수가 최종적으로 `ok`, `warn`, `fail` dict를 반환해야 한다. |

## 2. threshold 읽기: get_threshold_var

예제 스크립트의 첫 단계는 임계치 조회다.

```python
min_available_memory_percent = self.get_threshold_var(
    'min_available_memory_percent',
    default=10.0,
    value_type='float',
)
max_swap_usage_percent = self.get_threshold_var(
    'max_swap_usage_percent',
    default=50.0,
    value_type='float',
)
```

정확한 함수명은 `get_threshold_var`다. `get_threshhold`, `get_threshold`, `get_threshhold_var` 같은 함수는 현재 `_base.py`의 표준 API가 아니다.

### 2.1 어디에서 값을 가져오나

예제 케이스의 `case.json`에는 아래 값이 있다.

```json
"threshold_list": [
  {
    "name": "min_available_memory_percent",
    "value1": "10"
  },
  {
    "name": "max_swap_usage_percent",
    "value1": "50"
  }
]
```

`BaseCheck.get_threshold_var(...)`는 내부적으로 `item_payload.threshold_list`를 `{name: value1}` 형태로 바꾼 뒤 `key`와 같은 이름을 찾는다.

```python
def get_threshold_var(self, key, default=None, value_type=None, return_source=False):
    host_var = self.get_host_var(key=key)

    if host_var:
        return host_var

    mapped = self.get_threshold_list_map()
    raw_value = mapped.get(key)
    ...
```

조회 우선순위는 다음과 같다.

| 우선순위 | 위치 | 설명 |
| --- | --- | --- |
| 1 | `item_payload.host_vars[key]` | 값이 truthy이면 먼저 반환한다. 현재 구현상 이 경로는 타입 캐스팅을 거치지 않는다. |
| 2 | `item_payload.threshold_list[].name/value1` | 일반적인 threshold 조회 경로다. |
| 3 | `default` | key가 없거나 값이 비어 있거나 타입 변환에 실패하면 기본값을 반환한다. |

### 2.2 value_type

`value_type`은 `value1` 문자열을 어떤 타입으로 바꿀지 지정한다.

| value_type | 예 | 반환 |
| --- | --- | --- |
| `'int'` | `"80"` | `80` |
| `'float'` | `"10.5"` | `10.5` |
| `'bool'` | `"true"`, `"yes"`, `"1"` | `True` |
| `'str'` | `"a,b,c"` | `"a,b,c"` |
| `'raw'` | 원본 값 | 변환하지 않은 값 |

`value_type`을 생략하면 `default`의 타입으로 추론한다. 예를 들어 `default=10.0`이면 float로 변환한다.

### 2.3 활용 예시

숫자 임계치:

```python
max_cpu_usage_percent = self.get_threshold_var(
    'max_cpu_usage_percent',
    default=80.0,
    value_type='float',
)
```

문자열 목록:

```python
raw_keywords = self.get_threshold_var(
    'memory_error_keywords',
    default='ecc error|memory error|single-bit error',
    value_type='str',
)
keywords = [token.strip() for token in raw_keywords.split('|') if token.strip()]
```

값 출처 확인:

```python
threshold, source = self.get_threshold_var(
    'max_filesystem_usage_percent',
    default=85.0,
    value_type='float',
    return_source=True,
)
```

주의할 점:

- `case.json`의 `threshold_list[].name`과 `script.py`의 `get_threshold_var('...')` 문자열은 반드시 같아야 한다.
- 변환 실패 시 예외가 나지 않고 `default`로 돌아가므로, 임계치가 꼭 필요하면 별도 검증 분기를 둔다.
- `host_vars` 경로로 들어온 값은 현재 구현에서 바로 반환되므로 숫자 계산 전에 타입을 확인하는 것이 안전하다.

## 3. 명령 실행: _ssh

예제 스크립트는 `free` 명령을 SSH 경로로 실행한다.

```python
rc, out, err = self._ssh(FREE_COMMAND)
```

`BaseCheck._ssh(cmd, become=False)`의 핵심 동작은 다음과 같다.

```python
def _ssh(self, cmd, become=False):
    exec_cmd = cmd
    display_cmd = cmd
    if become:
        exec_cmd, display_cmd = self._build_ssh_become_command(cmd)

    rc, out, err = self.ctx['ssh'](
        exec_cmd,
        self.ctx['host'],
        self.ctx['port'],
        self.ctx['user'],
        self.ctx['password'],
        self.ctx['ssh_options'],
    )
    self._record_command(display_cmd, rc, out, err)
    return rc, out, err
```

반환값은 항상 세 개다.

| 값 | 의미 |
| --- | --- |
| `rc` | 명령 종료 코드. `0`이면 일반적으로 정상이다. |
| `out` | stdout 문자열이다. |
| `err` | stderr 문자열이다. |

replay mode에서는 `ctx['ssh']`가 실제 SSH 대신 `replay.json`의 fixture를 반환한다. live mode에서는 실제 대상 장비에 접속해 명령을 실행한다.

예제의 `replay.json`은 다음처럼 `_ssh('free')` 호출과 연결된다.

```json
[
  {
    "matcher_type": "exact",
    "matcher_value": "free",
    "rc": 0,
    "stdout_file": "outputs/free.stdout",
    "stderr": ""
  }
]
```

따라서 `script.py`의 `FREE_COMMAND = 'free'`와 `replay.json.matcher_value = "free"`가 다르면 replay mode에서 `REPLAY_MISS`가 날 수 있다.

### 3.1 precheck와 _ssh 실패 처리의 관계

운영 runner의 기본 흐름에서는 `skip_precheck=False`이므로 item 실행 전에 host precheck가 먼저 실행된다.

| 실행 흐름 | precheck 동작 |
| --- | --- |
| 일반 runner 실행 | SSH는 `true`, WinRM은 `Write-Output FAP_CONNECTION_OK`, Paramiko는 shell open으로 사전 연결 확인을 한다. |
| become credential 사용 | host precheck 뒤에 sudo, su, su - 권한상승 precheck를 별도로 수행한다. |
| `replay_cli.py` replay mode | fixture 기반 실행이라 `skip_precheck=True`로 실행한다. |
| `replay_cli.py --mode live` | 일반 runner를 호출하므로 precheck가 수행된다. |

따라서 새 스크립트에 별도 연결 상태체크 명령을 넣는 것은 중복이다. 아래 분기는 “연결을 다시 검사”하는 코드가 아니라, 실제 점검 명령을 실행했는데 실행 도중 연결성 오류처럼 보이는 결과가 돌아온 경우를 분류하는 방어적 처리다.

```python
if self._is_connection_error(rc, err):
    return self.fail(
        '호스트 연결 실패',
        metrics={
            'command': FREE_COMMAND,
            'rc': rc,
            'stderr_preview': (err or '').strip()[:300],
        },
        message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
    )

if rc != 0:
    return self.fail(
        '점검 명령 실행 실패',
        metrics={
            'command': FREE_COMMAND,
            'rc': rc,
            'stderr_preview': (err or '').strip()[:300],
        },
        message='free 명령 실행에 실패했습니다.',
    )
```

`_is_connection_error(rc, err)`는 `rc`가 `255`, `901`, `902`이거나 stderr에 `connection refused`, `permission denied`, `could not resolve hostname`, `paramiko_connection_error` 같은 연결 오류 문자열이 있는지 본다.

현장 작성 기준은 다음처럼 잡는다.

- 별도 연결 상태체크 명령은 넣지 않는다.
- 실제 점검 명령 실행 결과의 `rc`, `stdout`, `stderr`는 반드시 확인한다.
- `_is_connection_error(...)`는 필수 패턴이 아니라 오류 메시지를 더 명확히 나누고 싶을 때 사용한다.
- 운영 runner precheck 실패는 `script.py`가 실행되기 전에 runner가 `호스트 연결 실패` 결과를 만든다.
- replay mode는 precheck를 건너뛰므로 fixture의 오류 응답을 테스트하고 싶으면 스크립트 내부 실패 분기가 필요할 수 있다.

명령 특성상 결과 없음이 정상인 경우도 있다. 예를 들어 `grep`은 매칭이 없으면 `rc=1`을 반환할 수 있으므로 로그 검색 케이스에서는 아래처럼 `0`과 `1`을 모두 정상 실행으로 본다.

```python
if rc not in (0, 1):
    return self.fail(
        '점검 명령 실행 실패',
        metrics={
            'command': DMESG_MEMORY_COMMAND,
            'rc': rc,
            'stderr_preview': (err or '').strip()[:300],
        },
        message='dmesg 메모리 로그 점검 명령 실행에 실패했습니다.',
    )
```

## 4. 출력 파싱과 정책 판정

예제 스크립트는 `free` 출력에서 `Mem:` 행과 `Swap:` 행을 찾는다.

```python
lines = [line for line in (out or '').splitlines() if line.strip()]
mem_line = next((line for line in lines if line.strip().startswith('Mem:')), '')
swap_line = next((line for line in lines if line.strip().startswith('Swap:')), '')
```

출력 예시는 다음과 같다.

```text
               total        used        free      shared  buff/cache   available
Mem:        15726928     5016052     2362220      249868     8993692    10710876
Swap:        8060924      799920     7261004
```

파싱 단계는 실패 가능성을 잘게 나눈다.

| 실패 지점 | 반환 |
| --- | --- |
| 출력 줄이 부족함 | `self.fail('메모리 정보 없음', ...)` |
| `Mem:` 또는 `Swap:` 행이 없음 | `self.fail('메모리 정보 파싱 실패', ...)` |
| 컬럼 수가 예상과 다름 | `self.fail('메모리 정보 파싱 실패', ...)` |
| 숫자 변환 실패 | `self.fail('메모리 정보 파싱 실패', ...)` |
| 총 메모리가 0 이하 | `self.fail('메모리 총량 비정상', ...)` |

이렇게 나누면 현장에서 `result.json`만 보고도 명령 문제, 출력 형식 문제, 정책 위반을 구분할 수 있다. 연결 자체가 안 되는 문제는 보통 runner precheck 결과에서 먼저 차단되고, 실행 중 발생한 연결성 오류만 스크립트의 실패 분기로 들어온다.

정책 판정은 계산값과 threshold를 비교한다.

```python
available_memory_percent = round((mem_available_kib / mem_total_kib) * 100, 2)
swap_usage_percent = round((swap_used_kib / swap_total_kib) * 100, 2) if swap_total_kib > 0 else 0.0

if available_memory_percent < min_available_memory_percent:
    return self.fail(...)

if swap_usage_percent > max_swap_usage_percent:
    return self.fail(...)
```

정상일 때는 화면에 보여 줄 계산 근거를 `metrics`에 넣고, 사람이 읽을 요약을 `message`에 넣는다. threshold 값이나 판정 사유도 화면에서 필요하면 별도 필드보다 `metrics` 안에 같이 넣는 편이 현장 확인에 유리하다.

```python
return self.ok(
    metrics={
        'mem_total_kib': mem_total_kib,
        'available_memory_percent': available_memory_percent,
        'swap_usage_percent': swap_usage_percent,
        'min_available_memory_percent': min_available_memory_percent,
        'max_swap_usage_percent': max_swap_usage_percent,
    },
    message='free 기준 메모리 사용률 점검이 정상 수행되었습니다.',
)
```

## 5. 결과 반환: ok, warn, fail

`BaseCheck`의 결과 helper는 모두 Python dict를 반환한다. runner는 이 dict를 모아 `result.json`에 저장한다.

화면에서 주로 보이는 값은 다음처럼 단순하게 잡는다.

| 상태 | 스크립트에서 신경 쓸 값 | 설명 |
| --- | --- | --- |
| `ok` | `metrics`, `message` | 정상 관측값과 요약 메시지 |
| `warn` | `metrics`, `message` | 경고 관측값과 요약 메시지 |
| `fail` | `error`, `metrics`, `message` | 실패 유형, 관측값, 요약 메시지 |

`thresholds`, `reasons`, `stdout`, `stderr`, `raw_output` 같은 값은 helper나 result JSON에는 남길 수 있지만 화면상에서는 보이지 않거나 중요도가 낮다. 현장용 스크립트 예시는 화면에 보이는 값 중심으로 작성한다.

### 5.1 ok

`ok`는 점검이 정상일 때 쓴다.

```python
return self.ok(
    metrics={'available_memory_percent': 68.11},
    message='메모리 사용률 점검 정상',
)
```

화면 기준 주요 값:

```json
{
  "status": "ok",
  "metrics": {
    "available_memory_percent": 68.11
  },
  "message": "메모리 사용률 점검 정상"
}
```

`status`, `inspection_code`, `item_id`, `raw_output` 같은 값은 helper와 runner가 자동으로 붙이거나 내부 확인용으로 남긴다. 화면 표시를 위해서는 `metrics`와 `message`가 핵심이다.

### 5.2 warn

`warn`은 명령은 정상 실행됐고 점검도 수행됐지만 운영자가 확인해야 할 조건이 있을 때 쓴다.

예: 로그 키워드가 발견됐지만 장비 접속이나 파싱 자체는 성공한 경우.

```python
if matches:
    return self.warn(
        metrics=metrics,
        message='메모리 오류 관련 dmesg 로그가 확인되었습니다.',
    )
```

`warn`도 화면 기준으로는 `metrics`와 `message`를 채운다. 현장 결과 가독성을 위해 `message`는 항상 명시한다.

### 5.3 fail

`fail`은 명령 실패, 파싱 실패, 정책 실패에 쓴다. 연결 자체가 안 되는 문제는 보통 runner precheck가 먼저 `fail` 결과를 만들고, 스크립트 내부에서는 실제 명령 실행 중 발생한 연결성 오류를 필요할 때만 `fail`로 분류한다.

```python
return self.fail(
    '점검 명령 실행 실패',
    metrics={
        'command': FREE_COMMAND,
        'rc': rc,
        'stderr_preview': (err or '').strip()[:300],
    },
    message='free 명령 실행에 실패했습니다.',
)
```

화면 기준 주요 값:

```json
{
  "status": "fail",
  "error": "점검 명령 실행 실패",
  "metrics": {
    "command": "free",
    "rc": 1,
    "stderr_preview": "..."
  },
  "message": "free 명령 실행에 실패했습니다."
}
```

정책 실패도 `fail`로 쓸 수 있다. 다만 “실패”와 “주의”의 기준은 점검 항목 정책에 맞춰야 한다. 예를 들어 백업 작업 실패, 디스크 기준 초과처럼 조치 대상이면 `fail`, 참고 로그 검출처럼 운영자가 판단해야 하는 상태면 `warn`을 쓰는 방식이 일반적이다.

### 5.4 metrics, message, error 작성 기준

| 필드 | 목적 | 좋은 예 |
| --- | --- | --- |
| `metrics` | 실제 관측값, 파싱 결과 | `{'swap_usage_percent': 9.92}` |
| `message` | 운영자가 읽는 요약 | `free 기준 메모리 사용률 점검이 정상 수행되었습니다.` |
| `error` | `fail`일 때 실패 유형 | `점검 명령 실행 실패`, `출력 파싱 실패`, `임계치 초과` |

적용 기준이나 판정 사유가 화면에 보여야 한다면 `thresholds`나 `reasons`에 따로 넣기보다 `metrics`에 `max_swap_usage_percent`, `decision_reason`처럼 넣는다. 명령 실패 원문도 화면에서 필요하면 `stderr_preview`, `stdout_preview`처럼 `metrics`에 짧게 넣는다.

## 6. Paramiko 실행: _run_paramiko_commands와 _run_paramiko

네트워크 장비나 대화형 CLI가 필요한 장비는 SSH exec보다 Paramiko interactive shell을 쓴다. 이때 표준 함수는 `_run_paramiko_commands`다.

`_run_paramiko`는 한 명령만 실행하고 `_ssh`와 비슷하게 `(rc, stdout, stderr)` 형태로 받고 싶을 때 쓰는 얇은 wrapper다.

```python
def _run_paramiko(self, command, **kwargs):
    results = self._run_paramiko_commands([command], **kwargs)
    if not results:
        return 1, '', 'paramiko command is empty'
    result = results[0]
    return result['rc'], result['stdout'], result['stderr']
```

### 6.1 기본 클래스 설정

Paramiko 케이스는 보통 아래처럼 시작한다.

```python
class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True
```

주요 설정:

| 설정 | 의미 |
| --- | --- |
| `CONNECTION_METHOD = 'paramiko'` | runner가 Paramiko용 credential 선택과 실행 경로를 사용한다. |
| `PARAMIKO_PROFILE` | pager 패턴과 pager 응답을 결정한다. 예: `generic_network`, `cisco_ios`, `junos`, `solaris` |
| `PARAMIKO_REUSE_SESSION` | 같은 runner 프로세스에서 동일 접속 조건의 shell 세션을 재사용할지 결정한다. |
| `PARAMIKO_TIMEOUT_SEC` | 명령 prompt 대기 시간 기본값이다. |
| `PARAMIKO_READ_TIMEOUT_SEC` | 출력 수신 안정화 대기 시간이다. |
| `PARAMIKO_AUTH_METHOD` | `auto`, `key`, `password` 중 하나다. |

### 6.2 _run_paramiko_commands 반환 구조

호출 예:

```python
results = self._run_paramiko_commands(['show mac', 'show arp'], profile=self.PARAMIKO_PROFILE)
```

반환값은 명령별 dict 목록이다.

```json
[
  {
    "command": "show mac",
    "display_command": "show mac",
    "hide_command": false,
    "rc": 0,
    "stdout": "...",
    "stderr": "",
    "raw_output": "...",
    "timed_out": false,
    "prompt": "switch#"
  }
]
```

주요 필드:

| 필드 | 의미 |
| --- | --- |
| `command` | 실제 전송한 명령이다. |
| `display_command` | 결과 이력에 표시할 명령이다. `hide_command=True`이면 `*******`가 된다. |
| `rc` | `0`은 prompt 수신 성공, `124`는 prompt timeout, `255`는 접속/세션 오류다. |
| `stdout` | 명령 echo와 prompt를 제거한 출력이다. |
| `stderr` | timeout 또는 연결 오류 메시지다. |
| `raw_output` | 장비에서 받은 원문에 가까운 출력이다. |
| `timed_out` | prompt를 받지 못해 timeout이 났는지 표시한다. |
| `prompt` | 마지막으로 학습한 장비 prompt다. |

### 6.3 여러 명령 실행 예시

Piolink MAC/ARP 케이스는 두 명령을 같은 shell 세션에서 실행한다.

```python
COMMANDS = ['show mac', 'show arp']

results = self._run_paramiko_commands(COMMANDS, profile=self.PARAMIKO_PROFILE)
if not results:
    return None, self.fail(
        '점검 명령 실행 실패',
        metrics={'commands': COMMANDS, 'result_count': 0},
        message='Paramiko 명령 실행 결과가 비어 있습니다.',
    )
if len(results) < len(COMMANDS):
    return None, self.fail(
        '점검 명령 실행 실패',
        metrics={'commands': COMMANDS, 'result_count': len(results)},
        message='일부 점검 명령 결과를 수신하지 못했습니다.',
    )

for result in results:
    stdout = (result.get('stdout') or '').strip()
    stderr = (result.get('stderr') or '').strip()
    if result.get('rc') != 0:
        return None, self.fail(
            '점검 명령 실행 실패',
            metrics={
                'command': result.get('command'),
                'rc': result.get('rc'),
                'stderr_preview': stderr[:300],
            },
            message=f'{result.get("command")} 명령 실행에 실패했습니다.',
        )
```

이 패턴의 핵심은 세 가지다.

- 결과 목록이 비어 있는지 확인한다.
- 실행한 명령 수만큼 결과가 왔는지 확인한다.
- 각 결과의 `rc`를 확인하고 실패 시 화면에 필요한 `command`, `rc`, `stderr_preview`를 `metrics`에 남긴다.

### 6.4 enable 모드와 hide_command

Cisco tutorial 케이스는 enable 비밀번호 입력을 `hide_command=True`로 숨긴다.

```python
results = self._run_paramiko_commands([
    {
        'command': 'enable',
        'ignore_prompt': True,
    },
    {
        'command': enable_password,
        'hide_command': True,
    },
    {
        'command': 'show clock',
    },
])
```

명령 dict에서 자주 쓰는 옵션은 다음과 같다.

| 옵션 | 의미 |
| --- | --- |
| `command` | 전송할 명령 문자열이다. |
| `timeout` | 해당 명령만 별도 timeout을 적용한다. |
| `delay` | 명령 전송 전 대기 시간이다. |
| `ignore_prompt` | timeout이 나도 다음 명령으로 이어갈 수 있게 한다. enable 진입처럼 prompt가 바뀌는 상황에 쓴다. |
| `hide_command` | 비밀번호나 Ctrl-C 같은 입력을 결과 이력에서 `*******`로 숨긴다. |

`hide_command=True`는 raw output에서 실제 입력 문자열을 마스킹한다. credential, token, password 값은 `replay.json`, `result.json`, 문서, 로그에 남기지 않는 것이 원칙이다.

### 6.5 Paramiko replay 작성 포인트

Paramiko replay는 terminal 이벤트를 순서대로 맞춰야 한다.

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
  }
]
```

비밀번호 입력은 실제 값을 쓰지 말고 `redacted: true`를 사용한다.

## 7. _base.py를 현장에서 읽는 방법

`_base.py`를 처음부터 끝까지 읽으려고 하면 오래 걸린다. 스크립트 분석 중에는 호출한 함수에서 출발해 필요한 주변 함수만 따라간다.

### 7.1 SSH 케이스에서 볼 위치

SSH 기반 스크립트라면 주로 아래 함수만 보면 된다.

| 함수 | 확인 이유 |
| --- | --- |
| `_ssh` | 명령이 실제로 어떻게 실행되고 command history가 어떻게 남는지 확인한다. |
| `_is_connection_error` | precheck 이후 실제 명령 실행 중 돌아온 rc/stderr를 연결성 오류로 분류할 필요가 있는지 확인한다. |
| `get_threshold_var` | threshold 조회 우선순위와 타입 변환을 확인한다. |
| `ok`, `warn`, `fail` | 화면에 보이는 `metrics`, `message`, fail의 `error`가 어떻게 만들어지는지 확인한다. |
| `_resolve_raw_output` | 내부 result JSON의 raw_output 자동 생성 방식을 확인한다. 화면 표시용 필드는 아니다. |

분석 절차:

1. runner가 precheck를 수행하는 일반 실행인지, `replay_cli.py` replay처럼 `skip_precheck=True`인지 확인한다.
2. `script.py`에서 `_ssh(COMMAND)`를 찾는다.
3. `_base.py`의 `_ssh`에서 `self.ctx['ssh'](...)` 호출 인자를 확인한다.
4. `_record_command(...)`가 호출되는지 확인한다.
5. `ok/warn/fail` 호출부가 화면 표시용 `metrics`, `message`, fail의 `error`를 충분히 채우는지 확인한다.

### 7.2 Paramiko 케이스에서 볼 위치

Paramiko 기반 스크립트라면 아래 순서로 본다.

| 함수 | 확인 이유 |
| --- | --- |
| `_normalize_paramiko_commands` | 명령 목록, dict 옵션, `hide_command` 처리 방식을 확인한다. |
| `_resolve_paramiko_profile` | pager 패턴과 profile 이름이 유효한지 확인한다. |
| `_run_paramiko_commands` | 세션 생성, 명령 전송, prompt 대기, rc 생성 흐름을 확인한다. |
| `_paramiko_expect` | prompt timeout이나 pager 처리가 어떻게 되는지 확인한다. |
| `_build_paramiko_result` | 결과 dict 필드를 확인한다. |
| `_paramiko_reuse_session_enabled` | 세션 재사용 우선순위를 확인한다. |

분석 절차:

1. `CONNECTION_METHOD = 'paramiko'`인지 확인한다.
2. `PARAMIKO_PROFILE` 값을 확인하고 `_base.py`의 `PARAMIKO_PROFILES`에 있는지 본다.
3. `_run_paramiko_commands([...])`의 명령 수와 옵션을 확인한다.
4. timeout이 의도된 것인지, 실제 실패인지 `rc=124`, `timed_out`, `ignore_prompt`로 구분한다.
5. password나 enable secret 입력에는 `hide_command=True` 또는 replay의 `redacted: true`가 있는지 확인한다.

### 7.3 내부 raw_output이 만들어지는 흐름

`_ssh`와 `_run_paramiko_commands`는 내부에서 `_record_command(...)`를 호출한다. 이후 `ok`, `warn`, `fail`이 반환될 때 `_resolve_raw_output(...)`이 command history를 읽어 아래 같은 형태의 raw output을 만든다.

```text
[점검 단계 1]
 - 실행 명령어: free
 - 명령 종료코드: rc=0 (정상 종료)
 - 출력 내용: ...
```

따라서 점검 스크립트에서 `raw_output`을 매번 직접 만들 필요는 없다. 화면에서 필요한 값은 `metrics`, `message`, fail의 `error`에 담고, 내부 원문 이력은 helper가 자동으로 남기게 둔다.

## 8. 현장 디버깅 체크리스트

### 8.1 replay가 실패할 때

- `script.py`의 명령 문자열과 `replay.json.matcher_value`가 같은가?
- `script.py`에서 실행하는 명령 순서와 `replay.json` 엔트리 순서가 같은가?
- 긴 stdout 파일 경로가 `outputs/*.stdout`로 실제 존재하는가?
- Paramiko terminal replay에서 `recv`, `send`, prompt 순서가 실제 흐름과 같은가?
- password 입력이 `redacted: true`로 처리됐는가?

### 8.2 live mode가 실패할 때

- `CONNECTION_METHOD`가 대상 장비 접속 방식과 맞는가?
- credential type이 SSH, WINRM, NETWORK_DEVICE 중 맞는 값으로 선택되는가?
- precheck에서 막힌 실패인지, 실제 점검 명령 실행 중 발생한 실패인지 구분했는가?
- 명령 자체가 대상 OS나 장비 CLI에서 지원되는가?
- `grep`처럼 `rc=1`이 정상일 수 있는 명령을 무조건 실패 처리하지 않았는가?
- Paramiko prompt가 바뀌는 명령에 `ignore_prompt`나 적절한 timeout이 필요한가?
- pager가 걸리는 장비라면 `PARAMIKO_PROFILE`의 pager 패턴이 맞는가?

### 8.3 결과 품질을 확인할 때

- `metrics`만 보고 실제 관측값과 적용 기준을 재현할 수 있는가?
- `message`가 현장 운영자가 읽을 수 있는 문장인가?
- `fail` 결과의 `error`가 실패 유형을 짧고 명확하게 말하는가?
- 실패 원인 분석에 필요한 `rc`, `command`, 출력 preview가 `metrics`에 들어 있는가?
- 내부 `raw_output`에 credential, token, password, 개인키 원문이 없는가?

## 9. 새 스크립트 작성 시 최소 골격

SSH 기반 최소 골격:

```python
# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'uptime'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh(COMMAND)

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                metrics={
                    'command': COMMAND,
                    'rc': rc,
                    'stderr_preview': (err or '').strip()[:300],
                },
                message=f'{COMMAND} 명령 실행에 실패했습니다.',
            )

        output = (out or '').strip()
        if not output:
            return self.fail(
                '출력 없음',
                metrics={
                    'command': COMMAND,
                    'rc': rc,
                    'stdout_line_count': 0,
                },
                message='명령은 성공했지만 stdout이 비어 있습니다.',
            )

        return self.ok(
            metrics={'stdout_line_count': len(output.splitlines())},
            message='기본 SSH 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
```

Paramiko 기반 최소 골격:

```python
# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'show version'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def run(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return self.fail(
                '점검 명령 실행 실패',
                metrics={
                    'command': COMMAND,
                    'result_count': 0,
                },
                message='Paramiko 명령 실행 결과가 비어 있습니다.',
            )

        first = results[0]
        stdout = (first.get('stdout') or '').strip()
        stderr = (first.get('stderr') or '').strip()
        if first.get('rc') != 0:
            return self.fail(
                '점검 명령 실행 실패',
                metrics={
                    'command': COMMAND,
                    'rc': first.get('rc'),
                    'stderr_preview': stderr[:300],
                },
                message=f'{COMMAND} 명령 실행에 실패했습니다.',
            )

        if not stdout:
            return self.fail(
                '출력 없음',
                metrics={
                    'command': COMMAND,
                    'rc': first.get('rc'),
                    'stdout_line_count': 0,
                },
                message=f'{COMMAND} 결과가 비어 있습니다.',
            )

        return self.ok(
            metrics={'stdout_line_count': len(stdout.splitlines())},
            message='기본 Paramiko 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
```

## 10. 기억해야 할 핵심

- `script.py`의 `run()`은 항상 `ok`, `warn`, `fail` 중 하나의 결과 dict를 반환해야 한다.
- `get_threshold_var`는 `case.json`의 `threshold_list[].name`과 문자열이 같아야 한다.
- `_ssh`는 `(rc, out, err)`를 반환하고 command history를 자동 기록한다.
- `_run_paramiko_commands`는 명령별 결과 dict 목록을 반환한다.
- `_run_paramiko`는 단일 Paramiko 명령을 `_ssh`처럼 `(rc, stdout, stderr)`로 받고 싶을 때 쓰는 wrapper다.
- `ok`는 정상, `warn`은 점검은 됐지만 주의가 필요한 상태, `fail`은 명령/파싱/정책 실패에 쓴다.
- 화면 표시 기준으로 `ok`, `warn`은 `metrics`, `message`를 채우고, `fail`은 `error`, `metrics`, `message`를 채운다.
- 현장에서 `_base.py`를 볼 때는 전체를 읽기보다 `script.py`가 호출한 함수부터 따라간다.
- secret 값은 `hide_command`, `redacted`, placeholder를 사용하고 결과 파일에 남기지 않는다.
