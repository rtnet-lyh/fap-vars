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
