# Windows `_run_ps` Tutorial Guide

Windows 튜토리얼은 `CONNECTION_METHOD = 'winrm'`와 `_run_ps(...)` 사용 패턴을 단계별로 보여준다.

## 접속 정보

- Host: `172.20.2.100`
- Protocol: `WINRM`
- Port: `5986`
- User: `lyh`
- Password: `f3dtop0!`
- WinRM Transport: `ntlm`
- Server Cert Validation: `ignore`

## 예시 목록

1. `windows_winrm_01_hostname_check`
   `hostname` 단일 문자열 결과 처리
2. `windows_winrm_02_os_info_check`
   `Get-CimInstance Win32_OperatingSystem` JSON 파싱
3. `windows_winrm_03_disk_inventory_check`
   `Win32_LogicalDisk` 배열 JSON 파싱
4. `windows_winrm_04_winrm_service_check`
   서비스 상태와 threshold 비교
5. `windows_winrm_05_system_eventlog_check`
   `Get-WinEvent` 고급 필터 결과 JSON 파싱
6. `windows_winrm_06_powershell_script_check`
   multi-line PowerShell 스크립트와 `PSCustomObject` JSON 반환 예시

## 실행 예시

플랫폼 전체 replay:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/tutorial/windows
```

단일 케이스 replay:

```bash
python3 inspection_runtime/replay_cli.py \
  inspection_cases/tutorial/windows/windows_winrm_03_disk_inventory_check
```

단일 케이스 live:

```bash
python3 inspection_runtime/replay_cli.py --mode live \
  inspection_cases/tutorial/windows/windows_winrm_05_system_eventlog_check
```

## 작성 포인트

- Windows 튜토리얼은 `_run_ps(...)`를 사용하므로 `CONNECTION_METHOD = 'winrm'`와 `WINRM_SHELL = 'powershell'`를 함께 둔다.
- 포트 `5986`은 HTTPS endpoint로 접속하므로 `winrm_options.server_cert_validation = "ignore"`를 함께 둔다.
- PowerShell 결과는 가능한 한 `ConvertTo-Json`으로 고정하고 스크립트에서 JSON 파싱을 보여준다.

## `_run_ps(...)` 사용법

`_run_ps(command)`는 WinRM PowerShell 명령을 실행하고 `(rc, out, err)`를 반환한다.

```python
rc, out, err = self._run_ps('hostname')
```

- `rc`
  PowerShell 실행 종료코드다. 일반적으로 `0`이면 성공이다.
- `out`
  stdout 문자열이다. JSON으로 만들면 파싱이 쉬워진다.
- `err`
  stderr 문자열이다. WinRM progress CLIXML이 함께 섞일 수 있다.

기본 처리 순서는 아래 패턴을 권장한다.

```python
rc, out, err = self._run_ps(COMMAND)

if self._is_connection_error(rc, err):
    return self.fail(...)

if self._is_not_applicable(rc, err):
    return self.fail(...)

if rc != 0:
    return self.fail(...)
```

튜토리얼에서 `_run_ps(...)`를 쓸 때 포인트는 다음과 같다.

- 짧은 문자열 예시: `hostname`
- 객체 1건 예시: `Get-CimInstance ... | ConvertTo-Json`
- 배열 예시: `Get-CimInstance ... | ConvertTo-Json -Depth 4`
- 상태값 예시: `Get-Service -Name WinRM`
- 이벤트 로그 예시: `Get-WinEvent ... | ConvertTo-Json`

### PowerShell 스크립트 수행 예시

여러 줄 PowerShell 로직을 한 번에 실행하고 싶으면 multi-line 문자열로 스크립트를 만든 뒤 `_run_ps(...)`에 넘기면 된다.

```python
script = """
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$service = Get-Service -Name WinRM
$result = [PSCustomObject]@{
    ComputerName = $env:COMPUTERNAME
    WinRMStatus  = [string]$service.Status
    Is64Bit      = [Environment]::Is64BitOperatingSystem
}
$result | ConvertTo-Json -Depth 4
""".strip()

rc, out, err = self._run_ps(script)
```

이 방식은 아래 경우에 유용하다.

- 변수 선언과 조건문을 함께 쓰고 싶을 때
- 여러 cmdlet 결과를 하나의 `PSCustomObject`로 묶고 싶을 때
- 최종 결과를 `ConvertTo-Json`으로 고정해 파싱하고 싶을 때
