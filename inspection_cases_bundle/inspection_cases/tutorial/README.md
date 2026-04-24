# Tutorial Cases

이 디렉터리는 연결 방식별 튜토리얼 케이스 모음이다.

- `rocky/`: `CONNECTION_METHOD = 'ssh'`와 `_ssh(...)` 예시 6개
- `windows/`: `CONNECTION_METHOD = 'winrm'`와 `_run_ps(...)` 예시 6개
- `cisco_ios/`: `CONNECTION_METHOD = 'paramiko'`와 `_run_paramiko_commands(...)` 예시 5개
- `starters/`: UI 에디터 최초 노출용 `script.py` starter 템플릿 모음

플랫폼별 가이드는 아래 문서를 본다.

- [rocky/README.md](./rocky/README.md)
- [windows/README.md](./windows/README.md)
- [cisco_ios/README.md](./cisco_ios/README.md)
- [starters/README.md](./starters/README.md)

## UI Starter Templates

`starters/`는 실제 replay 실행용 케이스가 아니라, 사용자가 UI에서 `script.py`를 처음 볼 때 넣어줄 초기 템플릿 모음이다.

- `starters/script.py`
  UI에서 파일 하나만 보여줄 수 있을 때 사용하는 공통 단일 starter
  SSH / WinRM / Paramiko 예시 클래스 3개를 한 파일에 같이 둔 설명용 템플릿
- `starters/rocky_ssh_starter.py`
  `_ssh(...)` 호출, 실패 처리, stdout 파싱, `self.ok(...)` 반환의 최소 흐름
- `starters/windows_winrm_starter.py`
  `_run_ps(...)` 호출, WinRM 예외 처리, JSON 파싱, `self.ok(...)` 반환의 최소 흐름
- `starters/cisco_ios_paramiko_starter.py`
  `_run_paramiko_commands(...)` 호출, 명령 배열 처리, 결과 리스트 파싱, `self.ok(...)` 반환의 최소 흐름

권장 사용 기준:

- UI가 파일 하나만 지원하면: `script.py`
- Rocky/Linux 계열 UI 초기값: `rocky_ssh_starter.py`
- Windows 계열 UI 초기값: `windows_winrm_starter.py`
- Cisco IOS 계열 UI 초기값: `cisco_ios_paramiko_starter.py`

## 실행 방법

플랫폼 전체 replay:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/tutorial/rocky
python3 inspection_runtime/replay_cli.py inspection_cases/tutorial/windows
python3 inspection_runtime/replay_cli.py inspection_cases/tutorial/cisco_ios
```

단일 케이스 live:

```bash
python3 inspection_runtime/replay_cli.py --mode live \
  inspection_cases/tutorial/rocky/rocky_ssh_01_basic_identity_check

python3 inspection_runtime/replay_cli.py --mode live \
  inspection_cases/tutorial/windows/windows_winrm_01_hostname_check

python3 inspection_runtime/replay_cli.py --mode live \
  inspection_cases/tutorial/cisco_ios/cisco_ios_paramiko_01_show_clock_check
```

## 메모

- `starters/` 파일은 학습용 초기값이고, `rocky/`, `windows/`, `cisco_ios/` 아래 파일은 실행 가능한 튜토리얼 케이스다.
- 이 튜토리얼은 요청에 따라 각 `case.json`에 실제 live 접속 정보를 직접 포함한다.
- replay 응답은 학습용 fixture이고, live는 실제 장비/서버 상태에 따라 출력이 달라질 수 있다.
