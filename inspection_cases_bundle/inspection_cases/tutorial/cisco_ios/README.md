# Cisco IOS `_run_paramiko_commands` Tutorial Guide

Cisco IOS 튜토리얼은 `CONNECTION_METHOD = 'paramiko'`와 `_run_paramiko_commands(...)` 사용 패턴을 단계별로 보여준다.

## 접속 정보

- Host: `192.168.1.55`
- Protocol: `SSH`
- Port: `22`
- User: `admin`
- Password: `admin`
- Enable: `true`
- Enable Password: `admin`

## 예시 목록

1. `cisco_ios_paramiko_01_show_clock_check`
   `show clock` 기본 수집
2. `cisco_ios_paramiko_02_show_version_check`
   `terminal length 0` + `show version`
3. `cisco_ios_paramiko_03_interface_brief_check`
   `show ip interface brief` 파싱과 threshold 비교
4. `cisco_ios_paramiko_04_running_hostname_check`
   `show running-config | include ^hostname` 파싱
5. `cisco_ios_paramiko_05_running_config_check`
   dict command 형식의 `timeout`과 긴 출력 replay 파일 예시

## 실행 예시

플랫폼 전체 replay:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/tutorial/cisco_ios
```

단일 케이스 replay:

```bash
python3 inspection_runtime/replay_cli.py \
  inspection_cases/tutorial/cisco_ios/cisco_ios_paramiko_03_interface_brief_check
```

단일 케이스 live:

```bash
python3 inspection_runtime/replay_cli.py --mode live \
  inspection_cases/tutorial/cisco_ios/cisco_ios_paramiko_05_running_config_check
```

## 작성 포인트

- Cisco IOS 튜토리얼은 모두 `PARAMIKO_PROFILE = 'cisco_ios'`를 사용한다.
- 튜토리얼은 `PARAMIKO_ENABLE_MODE`와 `PARAMIKO_AUTH_METHOD`를 쓰지 않고, `enable` 진입도 명령 배열로 직접 보여준다.
- 기본 흐름은 아래 순서다.

```python
[
    {'command': 'enable', 'ignore_prompt': True},
    {'command': enable_password, 'hide_command': True},
    {'command': 'terminal length 0'},
    {'command': 'show version'},
]
```

- `ignore_prompt`
  `enable` 직후 장비가 기존 prompt 대신 `Password:`를 내보내므로, 첫 단계 timeout을 허용하고 다음 명령으로 넘길 때 사용한다.
- `hide_command`
  enable 비밀번호 입력 단계에서 raw output과 command history에 실제 비밀번호 대신 `*******`를 남길 때 사용한다.
- 수동 enable 흐름에서는 비밀번호 입력 다음 결과의 `prompt`가 `#`로 끝나는지 확인해서 privileged mode 진입 성공 여부를 판정한다.
- live 모드의 초기 접속 실패는 runner precheck에서 먼저 걸러지므로, 튜토리얼 스크립트는 명령 결과와 파싱 흐름 설명에 집중한다.
- 긴 출력은 `terminal length 0`를 먼저 보내고, replay에서는 `stdout_file`로 분리하는 편이 안전하다.

## `_run_paramiko_commands(...)` 사용법

`_run_paramiko_commands(commands)`는 Paramiko interactive shell 세션에서 여러 명령을 순차 실행하고 결과 리스트를 반환한다.

```python
results = self._run_paramiko_commands([
    {'command': 'enable', 'ignore_prompt': True},
    {'command': enable_password, 'hide_command': True},
    {'command': 'terminal length 0'},
    {'command': 'show version'},
])
```

반환값은 명령별 dict 리스트다.

- `command`
  실제 실행한 명령 문자열
- `display_command`
  로그 표시용 명령 문자열
- `rc`
  명령 종료코드
- `stdout`
  명령 출력
- `stderr`
  오류 출력
- `timed_out`
  프롬프트를 못 받아 timeout 되었는지 여부
- `prompt`
  해당 단계에서 학습한 최신 prompt

`commands`는 문자열 배열도 가능하지만, 튜토리얼에서는 dict 형식을 권장한다.

- `command`
  실제 전송할 문자열
- `timeout`
  해당 명령에만 적용할 timeout 초
- `ignore_prompt`
  프롬프트를 못 만나도 timeout 후 다음 명령으로 계속 진행
- `hide_command`
  raw output과 command history에는 `*******`로 기록

기본 실패 처리는 아래처럼 한다.

```python
failed = [
    item for item in results
    if item.get('rc') != 0 and not (item.get('command') == 'enable' and item.get('timed_out'))
]
if failed:
    return self.fail(...)
```

Cisco IOS 튜토리얼에서 핵심 패턴은 아래 3가지다.

- enable 진입: `enable` -> 비밀번호 입력
- paging 비활성화: `terminal length 0`
- show 계열 수집: `show clock`, `show version`, `show ip interface brief`, `show running-config`
