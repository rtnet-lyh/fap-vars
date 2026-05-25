# 점검 스크립트 Live Mode 테스트 가이드

`inspection_cases_bundle`에서 작성한 점검 케이스를 실제 테스트 대상에 붙여 `--mode live`로 검증하기 위한 가이드입니다. 이 문서는 운영 반영용 절차가 아니라, 테스트 호스트 또는 테스트 장비에서 단일 케이스가 정상 동작하는지 확인하는 절차에 초점을 둡니다.

## 1. Live Mode 테스트의 목적

Live mode 테스트는 `replay.json` fixture가 아니라 실제 대상 장비, 서버, API에 접속해 `script.py`가 동작하는지 확인합니다.

확인해야 할 핵심은 다음입니다.

- 실제 credential로 연결이 되는가
- `script.py`의 명령이 대상 환경에서 실행되는가
- 명령 출력 파싱이 실제 출력 형식과 맞는가
- threshold 판정이 기대대로 동작하는가
- `result.json`에 운영자가 판단할 수 있는 `metrics`, `thresholds`, `message`, `reasons`가 남는가

## 2. Replay Mode와 Live Mode 차이

| 구분 | Replay Mode | Live Mode |
| --- | --- | --- |
| 실행 대상 | `replay.json`에 기록된 fixture | 실제 테스트 호스트, 장비, API |
| 접속 여부 | 실제 접속 없음 | 실제 SSH, WinRM, Paramiko, API 접속 |
| 주요 목적 | 로직 재현성 검증 | 실제 환경 호환성 검증 |
| 산출물 | `result.json` | `result.json` |
| 위험도 | 낮음 | 높음 |
| 실행 범위 | 단일, 분류, 전체 가능 | 단일 케이스만 실행 |

Live mode는 실제 대상에 명령을 실행하므로 반드시 테스트 대상에서만 먼저 검증합니다.

## 3. Live Mode 테스트 기본 원칙

- live 실행은 단일 케이스만 수행합니다.
- 운영 장비가 아니라 테스트 호스트 또는 테스트 장비를 우선 사용합니다.
- 명령은 조회성 read-only 명령만 사용합니다.
- 파일 삭제, 서비스 재시작, 설정 변경, DB 쓰기, credential 갱신 명령은 live 테스트에 넣지 않습니다.
- `case.json`에 운영 비밀번호, 토큰, 개인키 원문을 커밋하지 않습니다.
- live 실행 전 반드시 replay mode로 먼저 검증합니다.
- live 실행 후 생성된 `result.json`에 secret이 섞였는지 확인합니다.

## 4. Live Mode 테스트 전 준비

테스트 전에 아래 항목을 확인합니다.

1. 테스트 대상이 명확한가?
   - 테스트 서버, 테스트 Windows 호스트, 테스트 네트워크 장비, 테스트 ESXi 등

2. 접속 방식이 맞는가?
   - Linux, Rocky, Unix: `ssh`
   - Windows: `winrm`
   - Network 대화형 장비: `paramiko`
   - ESXi/API 기반: `USE_HOST_CONNECTION = False`와 helper/API payload

3. `script.py` 명령이 안전한가?
   - 조회 명령인지 확인합니다.
   - `rm`, `mv`, `systemctl restart`, 설정 변경, DB update 같은 명령은 제외합니다.

4. `case.json` credential이 테스트용인가?
   - 운영 계정, 운영 비밀번호, 운영 토큰을 문서나 커밋 대상에 넣지 않습니다.

5. replay mode가 먼저 성공했는가?
   - live 테스트 전에 fixture 기반 로직 검증을 끝냅니다.

## 5. 권장 테스트 순서

### 5.1 케이스 경로 확인

예시 케이스 경로:

```text
inspection_cases/server/rocky/rocky_cpu_usage_procstat_check
```

### 5.2 Replay Mode 선검증

번들 루트(`inspection_cases_bundle/`)에서 실행합니다.

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/server/rocky/<case_name>
```

확인 항목:

- `result.json.results[].status`가 기대와 같은지
- `metrics`가 비어 있지 않은지
- `thresholds`가 실제 적용값을 담고 있는지
- `message`가 사람이 읽을 수 있는지
- `replay.json`의 `matcher_value`가 실제 명령 문자열과 같은지

### 5.3 Live Mode 단일 케이스 실행

replay 검증이 끝난 뒤 단일 케이스만 live mode로 실행합니다.

```bash
python3 inspection_runtime/replay_cli.py --mode live inspection_cases/server/rocky/<case_name>
```

저장소 루트(`fap-vars/`)에서 실행할 경우:

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py --mode live inspection_cases_bundle/inspection_cases/server/rocky/<case_name>
```

분류 디렉터리나 전체 `inspection_cases`에 live mode를 걸지 않습니다.

나쁜 예:

```bash
python3 inspection_runtime/replay_cli.py --mode live inspection_cases
```

## 6. Live 테스트용 `script.py` 작성 패턴

### 6.1 Linux, Rocky, Unix SSH 테스트 패턴

```python
# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'hostnamectl'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh(COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '명령 실행 실패',
                message='Live mode 테스트 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        output = (out or '').strip()
        if not output:
            return self.fail(
                '출력 없음',
                message='명령은 성공했지만 stdout이 비어 있습니다.',
                stdout=output,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'command': COMMAND,
                'stdout_line_count': len(output.splitlines()),
            },
            thresholds={},
            reasons='테스트 명령이 정상 실행되고 stdout이 수집되었습니다.',
            message='Live mode SSH 테스트가 정상입니다.',
            raw_output=output,
        )


CHECK_CLASS = Check
```

테스트용 명령은 `hostnamectl`, `uname -a`, `uptime`, `df -h`, `free -m`처럼 조회성 명령을 사용합니다.

### 6.2 Windows WinRM 테스트 패턴

```python
# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'Get-ComputerInfo | Select-Object -First 1'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        rc, out, err = self._run_ps(COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경 미지원',
                message='대상 환경에서 WinRM 테스트를 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                'PowerShell 명령 실행 실패',
                message='Live mode Windows 테스트 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        output = (out or '').strip()
        return self.ok(
            metrics={
                'command': COMMAND,
                'stdout_line_count': len(output.splitlines()),
            },
            thresholds={},
            reasons='WinRM PowerShell 테스트 명령이 정상 실행되었습니다.',
            message='Live mode WinRM 테스트가 정상입니다.',
            raw_output=output,
        )


CHECK_CLASS = Check
```

### 6.3 Network Paramiko 테스트 패턴

```python
# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'show version'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'
    PARAMIKO_REUSE_SESSION = False
    COMMAND_TIMEOUT = 10

    def run(self):
        result = self._run_paramiko_commands([
            {'command': COMMAND, 'timeout': self.COMMAND_TIMEOUT},
        ])[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()

        if result.get('rc') != 0:
            return self.fail(
                '네트워크 장비 명령 실행 실패',
                message='Paramiko live mode 테스트 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        if not stdout:
            return self.fail(
                '출력 없음',
                message='명령은 성공했지만 장비 출력이 비어 있습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        return self.ok(
            metrics={
                'command': COMMAND,
                'stdout_line_count': len(stdout.splitlines()),
            },
            thresholds={},
            reasons='Paramiko 테스트 명령이 정상 실행되고 출력이 수집되었습니다.',
            message='Live mode Paramiko 테스트가 정상입니다.',
            raw_output=stdout,
        )


CHECK_CLASS = Check
```

네트워크 장비는 pager, enable mode, prompt 차이 때문에 테스트 장비별 조정이 필요할 수 있습니다.

## 7. `case.json` live 테스트 체크포인트

`case.json`은 live mode에서 실제 접속 정보와 threshold를 제공합니다.

확인할 항목:

- `credentials`가 테스트 대상 접속 정보인지
- `host`, `port`, `user`, `password` 또는 연결 방식별 credential이 맞는지
- `item.threshold_list[].name`과 `script.py`의 `get_threshold_var(...)` 키가 일치하는지
- 운영 secret이 포함되어 있지 않은지
- 테스트 후 커밋 대상에 secret이 남지 않는지

threshold 예시:

```json
{
  "item": {
    "threshold_list": [
      {
        "name": "max_cpu_usage_percent",
        "value": 80
      }
    ]
  }
}
```

스크립트에서는 같은 키를 사용합니다.

```python
max_cpu_usage_percent = self.get_threshold_var(
    'max_cpu_usage_percent',
    default=80.0,
    value_type='float',
)
```

## 8. Live Mode 결과 확인 기준

live 실행 후 `result.json`에서 아래 항목을 확인합니다.

| 항목 | 확인 내용 |
| --- | --- |
| `status` | 기대한 `ok`, `warn`, `fail`인지 |
| `message` | 운영자가 바로 이해할 수 있는지 |
| `metrics` | 실제 측정값이 충분히 남았는지 |
| `thresholds` | 적용된 기준값이 남았는지 |
| `reasons` | 판정 이유가 명확한지 |
| `stdout`, `stderr`, `raw_output` | 디버깅 가능한 원문이 남았는지 |
| secret 노출 | 비밀번호, 토큰, 개인키가 결과에 섞이지 않았는지 |

특히 live mode에서는 `raw_output`과 `stdout`에 민감정보가 섞이지 않았는지 확인해야 합니다.

## 9. Live Mode 실패 시 분기 기준

### 9.1 연결 실패

증상:

- SSH timeout
- WinRM 인증 실패
- Paramiko banner timeout
- API endpoint 접속 실패

확인:

- 테스트 대상 IP와 port가 맞는지
- 방화벽 또는 접근 제어가 막고 있지 않은지
- credential이 테스트용으로 맞는지
- 연결 방식이 대상 OS 또는 장비와 맞는지

### 9.2 명령 실패

증상:

- `rc != 0`
- command not found
- permission denied

확인:

- 대상 OS에 해당 명령이 있는지
- 권한 상승이 필요한 명령인지
- `become=True`, sudo, su 설정이 필요한지
- 명령 문자열이 shell escaping 문제 없이 전달되는지

### 9.3 파싱 실패

증상:

- 명령은 성공했지만 `metrics` 생성 실패
- 실제 출력 포맷이 replay fixture와 다름

확인:

- 실제 live 출력과 `outputs/*.stdout` 샘플이 다른지
- locale, OS 버전, 장비 버전에 따라 컬럼명이 다른지
- regex가 너무 좁게 작성되어 있지 않은지

### 9.4 정책 실패

증상:

- 연결과 파싱은 성공했지만 threshold 초과

확인:

- threshold 값이 테스트 목적에 맞는지
- 단위가 맞는지
- 비교 연산이 맞는지
- `warn`과 `fail` 중 어떤 상태가 맞는지

## 10. Live Mode 테스트 완료 후 정리

테스트가 끝나면 아래를 확인합니다.

- `result.json`에 secret이 포함되어 있지 않은가?
- 테스트용 credential이 `case.json`에 남아 커밋될 위험이 없는가?
- live 테스트 때문에 변경된 산출물이 의도한 파일뿐인가?
- replay fixture도 실제 출력에 맞게 보강해야 하는가?
- 운영 대상에 실행해도 안전한 read-only 명령만 남아 있는가?

필요하면 live 테스트 후 `case.json`의 credential 값을 placeholder로 되돌립니다.

## 11. 최종 체크리스트

- live mode 실행 전 replay mode가 성공했는가?
- live mode는 단일 케이스로만 실행했는가?
- 테스트 대상이 운영 장비가 아닌가?
- `script.py` 명령이 read-only인가?
- 연결 실패, 명령 실패, 파싱 실패, 정책 실패가 구분되는가?
- `metrics`, `thresholds`, `reasons`, `message`가 충분한가?
- `result.json`에 secret이 남지 않았는가?
- 전체 `inspection_cases`에 live mode를 실행하지 않았는가?

