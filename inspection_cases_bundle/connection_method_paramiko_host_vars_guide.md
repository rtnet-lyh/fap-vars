# 연결 방식 및 Paramiko Host Vars 적용 가이드

이 문서는 점검 스크립트의 원격 연결 방식 결정 정책과 `PARAMIKO_*` 옵션 우선순위를 설명한다. 목적은 개별 `script.py`마다 반복해서 `CONNECTION_METHOD`, `PARAMIKO_BANNER_TIMEOUT_SEC` 같은 값을 넣지 않고, host vars 또는 실행 payload 설정으로 제어할 수 있게 하는 것이다.

## 1. 변경 목적

기존에는 점검 스크립트마다 `CONNECTION_METHOD = 'paramiko'`, `PARAMIKO_BANNER_TIMEOUT_SEC = 20` 같은 값을 직접 넣는 패턴이 많았다.

이 방식은 동작은 명확하지만, 호스트별 timeout, 인증 방식, 장비 profile이 달라질 때 각 점검 스크립트를 계속 수정해야 한다. 변경 후에는 공통 기본값은 런타임에 두고, 호스트별 차이는 `host_vars`로 덮어쓰는 방식을 권장한다.

권장 방향은 다음과 같다.

- 연결 방식은 스크립트 명시값, 실행 payload, 기본값 순서로 결정한다.
- `inspection_code` 값만 보고 연결 방식을 자동 판단하지 않는다.
- 신규 점검 스크립트에서는 `_ssh(...)`를 사용하지 않고 Paramiko 기반 `_run_paramiko_commands(...)`를 우선 사용한다.
- 기존 `_ssh(...)` 스크립트는 호환성을 위해 그대로 실행 가능하게 유지한다.
- `USE_HOST_CONNECTION`은 기본값이 `True`이므로 기본 스크립트 예시에서는 명시하지 않는다.
- Paramiko 옵션은 `host_vars`가 가장 우선한다.
- 스크립트 공통 기본값이 필요할 때만 `Check` class 상수로 둔다.
- 아무 것도 지정하지 않으면 기본 연결 방식은 `paramiko`이다.

## 2. 연결 방식 결정 우선순위

연결 방식은 `runner.get_connection_method(...)`에서 결정한다.

우선순위는 다음과 같다.

1. 모듈 레벨 `CONNECTION_METHOD`
2. `Check` class에 직접 정의한 `CONNECTION_METHOD`
3. item payload의 실행 계정 형식 또는 연결 방식 필드
4. 기본값 `paramiko`

지원하는 주요 값은 다음이다.

| 입력 값 | 연결 방식 |
| --- | --- |
| `ssh` 또는 `SSH` | `ssh` |
| `winrm` 또는 `WINRM` | `winrm` |
| `paramiko` 또는 `PARAMIKO` | `paramiko` |
| `NETWORK_DEVICE` | `paramiko` |

item payload에서 참조하는 필드는 다음 순서다.

1. `connection_method`
2. `execution_account_type`
3. `credential_type_name`
4. `credential_type`

실행 계정 형식이 payload에 포함된다면 스크립트에 `CONNECTION_METHOD`를 추가하지 않는다. `connection_method`는 실행 계정 형식만으로 표현하기 어려운 예외를 명시할 때 사용한다.

## 3. `inspection_code`는 연결 방식을 결정하지 않는다

이제 `inspection_code`가 `W-*`, `PC-*`처럼 보이더라도 자동으로 `winrm`이 되지 않는다.

예를 들어 아래 payload는 `inspection_code`가 Windows처럼 보여도 연결 방식 판단에 사용되지 않는다.

```json
{
  "inspection_code": "W-TEST-001"
}
```

위 경우 스크립트나 payload에 연결 방식이 없으면 기본값 `paramiko`가 사용된다.

Windows 점검은 `inspection_code`에 의존하지 말고 실행 계정 형식으로 `WINRM`을 전달한다.

```json
{
  "credential_type": "WINRM"
}
```

또는:

```json
{
  "credential_type_name": "WINRM"
}
```

위 값이 있으면 스크립트에 `CONNECTION_METHOD = 'winrm'`를 쓰지 않아도 된다. `WINRM_SHELL`도 기본값이 `powershell`이므로 일반적인 PowerShell 점검에서는 명시하지 않는다.

## 4. 기본값과 호환성

`BaseCheck.CONNECTION_METHOD`의 기본값은 `paramiko`이다.

다만 runner는 `BaseCheck`에서 상속된 기본값을 스크립트가 직접 지정한 값으로 보지 않는다. 즉 `Check` class에 `CONNECTION_METHOD`를 쓰지 않은 경우에는 payload 값이 우선 적용될 수 있다.

예시:

```python
class Check(BaseCheck):
    def run(self):
        return self.result(
            status='ok',
            message=self.ctx.get('connection_method'),
        )
```

payload:

```json
{
  "credential_type": "SSH"
}
```

결과:

```text
connection_method = ssh
```

payload에도 연결 방식이 없으면:

```text
connection_method = paramiko
```

기존에 아래처럼 명시한 스크립트는 호환성을 위해 계속 `ssh`로 실행된다.

```python
class Check(BaseCheck):
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh('hostname')
        return self.result(
            status='ok',
            raw_output=out,
        )
```

다만 신규 작성 또는 기능 개선 시에는 `_ssh(...)`를 새로 사용하지 않는다. `_ssh(...)`는 기존 코드 실행을 깨지 않기 위한 legacy 경로로만 본다.

## 5. `_ssh(...)`를 신규 스크립트에서 사용하지 않는 이유

신규 점검 스크립트는 `_ssh(...)` 대신 `_run_paramiko_commands(...)` 사용을 권장한다.

이유는 다음과 같다.

- 일부 서버 환경에서 SSH exec 방식만으로는 명령 실행 흐름을 안정적으로 구현하기 어려웠다.
- `su -`, `sudo` 같은 권한 상승 과정은 password prompt, shell 전환, prompt 변경을 처리해야 하는데 `_ssh(...)` 방식에서는 이 흐름을 일반화하기 어렵다.
- 권한 상승 후 여러 명령을 같은 세션에서 이어서 실행해야 하는 케이스가 있다.
- 장비나 서버마다 login banner, prompt, pager, shell 초기화 출력이 달라 단순 SSH 명령 실행보다 대화형 세션 처리가 필요하다.
- Paramiko 경로는 profile, timeout, become, command timeout, prompt 처리 같은 옵션을 `host_vars`로 조정할 수 있어 스크립트 수정 범위를 줄일 수 있다.

따라서 정책은 다음과 같다.

| 구분 | 정책 |
| --- | --- |
| 신규 Linux/Unix 서버 점검 | `_run_paramiko_commands(...)` 사용 |
| 권한 상승이 필요한 점검 | `_run_paramiko_commands(..., become=True)` 사용 |
| 네트워크/스토리지 등 대화형 장비 | `_run_paramiko_commands(...)` 사용 |
| 기존 `_ssh(...)` 스크립트 | 즉시 제거하지 않고 호환 유지 |
| 기존 `_ssh(...)` 스크립트 개선 작업 | 가능하면 Paramiko 방식으로 전환 검토 |

## 6. Paramiko 옵션 우선순위

Paramiko 관련 옵션은 다음 우선순위로 결정된다.

1. `host_vars`
2. `script.py`의 `Check` class 또는 모듈 상수
3. `BaseCheck` 기본값

예를 들어 `Check` class에 아래 값이 있어도:

```python
class Check(BaseCheck):
    PARAMIKO_BANNER_TIMEOUT_SEC = 20
```

host vars에 값이 있으면 host vars가 우선한다.

```json
{
  "host_vars": {
    "PARAMIKO_BANNER_TIMEOUT_SEC": 100
  }
}
```

실제 Paramiko 연결에는 다음 값이 들어간다.

```text
banner_timeout = 100.0
```

## 7. 중요한 주의사항: class attribute와 resolved option은 다르다

`host_vars`는 실제 실행 옵션을 덮어쓰지만, `self.PARAMIKO_BANNER_TIMEOUT_SEC` 같은 class attribute 자체를 바꾸지는 않는다.

아래 코드는 class에 정의된 값 또는 `BaseCheck` 기본값을 본다.

```python
self.PARAMIKO_BANNER_TIMEOUT_SEC
```

host vars까지 반영된 값을 확인하려면 아래처럼 본다.

```python
options = self._paramiko_options()
banner_timeout = options['banner_timeout_sec']
```

예시:

```python
class Check(BaseCheck):
    PARAMIKO_BANNER_TIMEOUT_SEC = 20

    def run(self):
        options = self._paramiko_options()
        return self.result(
            status='ok',
            message=(
                f"class={self.PARAMIKO_BANNER_TIMEOUT_SEC}, "
                f"resolved={options['banner_timeout_sec']}"
            )
        )
```

host vars:

```json
{
  "host_vars": {
    "PARAMIKO_BANNER_TIMEOUT_SEC": 100
  }
}
```

출력 예:

```text
class=20, resolved=100
```

따라서 점검 결과 메시지나 디버깅 로그에 실제 적용값을 표시하려면 반드시 `_paramiko_options()`를 사용한다.

## 8. 사용 예시

### 8.1 기본 Paramiko 스크립트

별도 `CONNECTION_METHOD`를 쓰지 않으면 기본값은 `paramiko`이다.

```python
# -*- coding: utf-8 -*-
from .common._base import BaseCheck


class Check(BaseCheck):
    def run(self):
        result = self._run_paramiko_commands('whoami', become=True)[-1]
        return self.result(
            status='ok',
            message='Paramiko 명령 실행 완료',
            raw_output=result.get('stdout', ''),
        )


CHECK_CLASS = Check
```

host vars로 timeout을 조정할 수 있다.

```json
{
  "host_vars": {
    "PARAMIKO_BANNER_TIMEOUT_SEC": 100,
    "PARAMIKO_AUTH_TIMEOUT_SEC": 30,
    "PARAMIKO_TIMEOUT_SEC": 10
  }
}
```

### 8.2 host vars 적용값 확인

실제 적용값을 점검 결과에 남기고 싶으면 `_paramiko_options()`를 사용한다.

```python
class Check(BaseCheck):
    PARAMIKO_BANNER_TIMEOUT_SEC = 20

    def run(self):
        options = self._paramiko_options()
        result = self._run_paramiko_commands('whoami', become=True)[-1]

        return self.result(
            status='ok',
            message=f"banner_timeout={options['banner_timeout_sec']}",
            raw_output=result.get('stdout', ''),
        )
```

host vars:

```json
{
  "host_vars": {
    "PARAMIKO_BANNER_TIMEOUT_SEC": 100
  }
}
```

결과 메시지:

```text
banner_timeout=100
```

### 8.3 기존 `_ssh(...)` 스크립트 호환

기존에 이미 `_ssh(...)`로 작성된 스크립트는 호환성을 위해 계속 실행할 수 있다. 이 경우 명시적으로 `ssh`를 지정한다.

```python
class Check(BaseCheck):
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh('uptime')
        if rc != 0:
            return self.result(
                status='fail',
                message='명령 실행 실패',
                stderr=err,
            )
        return self.result(
            status='ok',
            raw_output=out,
        )
```

이 패턴은 신규 작성 예시가 아니라 legacy 호환 예시다. 새 점검 스크립트에서는 같은 기능을 가능하면 아래처럼 Paramiko로 작성한다.

```python
class Check(BaseCheck):
    def run(self):
        result = self._run_paramiko_commands('uptime', become=True)[-1]
        if result.get('rc') != 0:
            return self.result(
                status='fail',
                message='명령 실행 실패',
                stderr=result.get('stderr', ''),
            )
        return self.result(
            status='ok',
            raw_output=result.get('stdout', ''),
        )
```

`_ssh(...)` 경로에서는 host vars의 `PARAMIKO_*` 옵션이 적용되지 않는다. 권한 상승, prompt, timeout을 host vars로 조정해야 한다면 Paramiko 방식으로 전환한다.

### 8.4 Windows WinRM 스크립트

Windows 점검은 실행 계정 형식이 `WINRM`이면 스크립트에서 연결 방식과 shell을 명시하지 않는다. 기본 shell은 `powershell`이다.

```python
class Check(BaseCheck):
    def run(self):
        rc, out, err = self._run_ps('Get-ComputerInfo | Select-Object -First 1')
        if rc != 0:
            return self.result(
                status='fail',
                message='PowerShell 실행 실패',
                stderr=err,
            )
        return self.result(
            status='ok',
            raw_output=out,
        )
```

`CONNECTION_METHOD = 'winrm'`는 payload에서 실행 계정 형식을 받을 수 없는 예외 상황에만 사용한다. `WINRM_SHELL`은 `cmd` 같은 다른 shell을 의도적으로 써야 할 때만 명시한다.

### 8.5 네트워크 장비 Paramiko profile

장비별 profile은 스크립트에 고정하지 말고 host vars에서 조정한다.

```python
class Check(BaseCheck):
    def run(self):
        result = self._run_paramiko_commands('show version')[0]
        return self.result(
            status='ok',
            raw_output=result.get('stdout', ''),
        )
```

host vars:

```json
{
  "host_vars": {
    "PARAMIKO_PROFILE": "cisco_ios",
    "PARAMIKO_BANNER_TIMEOUT_SEC": 60
  }
}
```

위 경우 스크립트에는 profile 코드가 없지만 실제 실행 profile은 `cisco_ios`가 된다. 모든 호스트가 같은 profile을 써야 하는 케이스에서만 `Check` class에 `PARAMIKO_PROFILE` 기본값을 둘 수 있다.

## 9. 권장 작성 패턴

새 점검 스크립트는 가능하면 아래 원칙을 따른다.

- Paramiko를 쓸 수 있으면 `CONNECTION_METHOD`를 생략한다.
- 신규 스크립트에서는 `_ssh(...)`를 사용하지 않는다.
- 기존 `_ssh(...)` 스크립트는 호환성 차원에서 유지하되, 수정 작업이 발생하면 Paramiko 전환을 검토한다.
- Windows는 실행 계정 형식 또는 payload의 `credential_type`, `credential_type_name`, `connection_method`로 `WINRM`을 전달하고, 스크립트에는 `_run_ps(...)`만 둔다.
- 최종 반환은 `self.ok(...)`, `self.fail(...)` 같은 상태별 helper가 아니라 `self.result(status=..., ...)`를 사용한다.
- 호스트별 timeout, profile, 인증 세부 옵션은 `host_vars`로 관리한다.
- 스크립트 안에서 실제 Paramiko 적용값을 확인할 때는 `_paramiko_options()`를 사용한다.
- `self.PARAMIKO_*` 값은 기본 class 설정 확인용으로만 본다.

## 10. 마이그레이션 체크리스트

기존 스크립트를 점검할 때 아래 항목을 확인한다.

- `CONNECTION_METHOD = 'ssh'`가 있는가?
  - 기존 `_ssh(...)` 스크립트라면 당장 제거하지 않고 유지한다.
  - 신규 작성에서는 사용하지 않는다.
  - 수정 작업이 들어가는 시점에는 `_run_paramiko_commands(..., become=True)` 방식으로 전환 가능한지 검토한다.
  - 이미 `_run_paramiko_commands(...)`만 쓰는 스크립트라면 제거해도 된다.

- `CONNECTION_METHOD = 'paramiko'`가 반복되어 있는가?
  - 기본값이 `paramiko`이므로 특별한 이유가 없으면 제거해도 된다.

- `PARAMIKO_BANNER_TIMEOUT_SEC`, `PARAMIKO_AUTH_TIMEOUT_SEC` 같은 값이 스크립트마다 반복되는가?
  - 호스트별 차이라면 `host_vars`로 옮긴다.
  - 케이스 공통 기본값이라면 `Check` class에 남겨도 된다.

- `inspection_code`가 `W-*`, `PC-*`라서 자동 WinRM이 되기를 기대하는가?
  - 더 이상 자동 판단하지 않는다.
  - 실행 계정 형식 또는 payload의 `credential_type`, `credential_type_name`, `connection_method`로 `WINRM`을 전달한다.
  - 스크립트의 `CONNECTION_METHOD = 'winrm'`는 payload로 연결 방식을 전달할 수 없는 예외 상황에만 사용한다.

- 결과 메시지에서 `self.PARAMIKO_BANNER_TIMEOUT_SEC`를 찍고 있는가?
  - host vars 반영값이 필요하면 `self._paramiko_options()['banner_timeout_sec']`로 바꾼다.

## 11. 테스트 포인트

변경 정책은 다음 테스트로 확인한다.

- `Check` class에 `CONNECTION_METHOD`가 있으면 payload보다 우선한다.
- payload `connection_method=ssh`이면 `ssh`로 실행된다.
- payload `credential_type_name=WINRM`이면 `winrm`으로 실행된다.
- 연결 방식이 없으면 기본값은 `paramiko`이다.
- `inspection_code=W-*`여도 연결 방식은 바뀌지 않는다.
- `host_vars.PARAMIKO_BANNER_TIMEOUT_SEC`는 `Check.PARAMIKO_BANNER_TIMEOUT_SEC`보다 우선한다.

운영 로그에서 확인할 때는 runner의 item start 로그를 본다.

```text
--- item start: inspection_code=TEST1 ... method=paramiko ...
```

그리고 실제 Paramiko option 값을 스크립트에서 확인하려면:

```python
options = self._paramiko_options()
print(options['banner_timeout_sec'])
```

또는 결과 메시지에 남긴다.

```python
return self.result(
    status='ok',
    message=f"banner={options['banner_timeout_sec']}",
)
```
