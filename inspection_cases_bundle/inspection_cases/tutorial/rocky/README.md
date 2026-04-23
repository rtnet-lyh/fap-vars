# Rocky `_ssh` Tutorial Guide

Rocky 튜토리얼은 `CONNECTION_METHOD = 'ssh'`와 `_ssh(...)` 사용 패턴을 단계별로 보여준다.

## 접속 정보

- Host: `192.168.1.123`
- Protocol: `SSH`
- Port: `22`
- User: `fap`
- Password: `f3dtop0!`
- Become: `true`
- Become Method: `su -`
- Become User: `root`
- Become Password: `f3dtop0!`

## 예시 목록

1. `rocky_ssh_01_basic_identity_check`
   `hostname && whoami` 기본 호출과 stdout 파싱
2. `rocky_ssh_02_os_release_check`
   `/etc/os-release` key/value 파싱
3. `rocky_ssh_03_root_filesystem_df_check`
   `df -h /` 파싱과 threshold 비교
4. `rocky_ssh_04_multi_command_health_check`
   `_ssh(...)` 여러 번 호출해 CPU, 메모리, uptime 함께 수집
5. `rocky_ssh_05_become_root_access_check`
   `su -` 권한상승 wrapper, marker 검증, password masking 예시

## 실행 예시

플랫폼 전체 replay:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/tutorial/rocky
```

단일 케이스 replay:

```bash
python3 inspection_runtime/replay_cli.py \
  inspection_cases/tutorial/rocky/rocky_ssh_03_root_filesystem_df_check
```

단일 케이스 live:

```bash
python3 inspection_runtime/replay_cli.py --mode live \
  inspection_cases/tutorial/rocky/rocky_ssh_05_become_root_access_check
```

## 작성 포인트

- `_ssh(...)`는 `rc, out, err`를 직접 받아서 연결 실패와 명령 실패를 분리한다.
- `become` 정보는 `credentials.LINUX[].credential_type_name == "APPLICATION"` 항목에 둔다.
- `su -` 예시는 `_ssh` 자체 기능이 아니라 스크립트 안에서 명령 문자열을 조합해 보여준다.
