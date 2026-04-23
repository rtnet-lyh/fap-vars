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
6. `rocky_ssh_06_shell_script_check`
   `_ssh(...)`에 `bash -lc` 스크립트를 넘겨 여러 줄 쉘 로직을 한 번에 실행하는 예시

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

## `_ssh(...)` 사용법

`_ssh(command)`는 현재 케이스의 SSH 접속 정보로 명령을 1회 실행하고 `(rc, out, err)`를 반환한다.

```python
rc, out, err = self._ssh('hostname && whoami')
```

- `rc`
  원격 명령 종료코드다. 일반적으로 `0`이면 성공이다.
- `out`
  stdout 문자열이다.
- `err`
  stderr 문자열이다.

기본 처리 순서는 아래 패턴을 권장한다.

```python
rc, out, err = self._ssh('command')

if self._is_connection_error(rc, err):
    return self.fail(...)

if rc != 0:
    return self.fail(...)
```

튜토리얼에서 `_ssh(...)`를 쓸 때 포인트는 다음과 같다.

- 단일 명령 예시: `hostname`, `cat /etc/os-release`, `df -h /`
- 다중 수집 예시: `_ssh(...)`를 여러 번 호출해 CPU, 메모리, uptime을 따로 모은다
- 권한상승 예시: `_ssh(...)` 자체에 become 옵션이 있는 것은 아니므로 `su -` 명령 문자열을 직접 조합한다

### 쉘 스크립트 수행 예시

여러 줄 쉘 로직을 한 번에 실행하고 싶으면 `bash -lc`로 감싸는 방식이 가장 단순하다.

```python
script = (
    "bash -lc "
    + __import__('shlex').quote(
        "hostname; "
        "echo '---'; "
        "df -h /; "
        "echo '---'; "
        "uptime"
    )
)
rc, out, err = self._ssh(script)
```

이 방식은 아래 경우에 유용하다.

- 여러 명령을 한 번의 SSH 호출로 묶고 싶을 때
- `if`, `for`, 파이프, 리다이렉션 같은 쉘 문법을 쓰고 싶을 때
- replay에서 `matcher_value`를 스크립트 문자열 그대로 맞출 수 있을 때

### 권한 상승 예시

Rocky 튜토리얼의 `_ssh(...)` 권한상승 예시는 `APPLICATION` credential의 `become_*` 값을 읽어 `su -` 명령 문자열을 직접 조합하는 방식이다.

```python
import shlex

become_password = str(self.get_application_credential_value('become_password', '') or '')
become_user = str(self.get_application_credential_value('become_user', 'root') or 'root')

inner_command = "whoami && ls /root >/dev/null && echo ROOT_DIR_ACCESS_OK"
command = "bash -lc " + shlex.quote(
    "printf '%s\\n' {password} | su - {user} -c {inner}".format(
        password=shlex.quote(become_password),
        user=shlex.quote(become_user),
        inner=shlex.quote("bash -lc " + shlex.quote(inner_command)),
    )
)
rc, out, err = self._ssh(command)
```

권한상승 결과를 검증할 때는 아래를 함께 보는 편이 안전하다.

- `whoami` 결과가 기대한 `root`인지
- root 전용 경로나 명령이 실제로 수행되는지
- `become_password`가 `_command_history`에 그대로 남지 않도록 masking 했는지
