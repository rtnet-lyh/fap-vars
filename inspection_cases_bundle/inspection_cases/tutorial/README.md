# Tutorial Cases

이 디렉터리는 연결 방식별 튜토리얼 케이스 모음이다.

- `rocky/`: `CONNECTION_METHOD = 'ssh'`와 `_ssh(...)` 예시 6개
- `windows/`: `CONNECTION_METHOD = 'winrm'`와 `_run_ps(...)` 예시 6개
- `cisco_ios/`: `CONNECTION_METHOD = 'paramiko'`와 `_run_paramiko_commands(...)` 예시 5개

플랫폼별 가이드는 아래 문서를 본다.

- [rocky/README.md](./rocky/README.md)
- [windows/README.md](./windows/README.md)
- [cisco_ios/README.md](./cisco_ios/README.md)

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

- 이 튜토리얼은 요청에 따라 각 `case.json`에 실제 live 접속 정보를 직접 포함한다.
- replay 응답은 학습용 fixture이고, live는 실제 장비/서버 상태에 따라 출력이 달라질 수 있다.
