# Starter Templates

이 디렉터리는 실제 replay 케이스가 아니라 UI 에디터의 최초 노출값으로 쓰기 위한 `script.py` starter 템플릿 모음이다.

- `script.py`
  UI에서 하나의 Python 파일만 보여줄 수 있을 때 사용하는 공통 starter 템플릿
  SSH / WinRM / Paramiko 예시 클래스 3개를 한 파일에 같이 둔다
- `rocky_ssh_starter.py`
  Rocky/Linux 사용자가 `_ssh(...)` 흐름을 바로 이해하도록 만든 기본 템플릿
- `windows_winrm_starter.py`
  Windows 사용자가 `_run_ps(...)`와 JSON 파싱 흐름을 바로 이해하도록 만든 기본 템플릿
- `cisco_ios_paramiko_starter.py`
  Cisco IOS 사용자가 `_run_paramiko_commands(...)` 배열 패턴을 바로 이해하도록 만든 기본 템플릿

## 사용 원칙

- 이 파일들은 `tutorial/*` 실행 예제를 대체하지 않는다.
- UI에서 파일 하나만 보여줘야 하면 `script.py`를 기본값으로 사용한다.
- `script.py`는 분기형이 아니라 예시 클래스 3개를 나란히 보여주는 설명용 파일이다.
- UI에서 플랫폼별로 다른 초기값을 넣을 수 있으면 OS별 starter를 사용한다.
- starter의 목적은 "바로 실행"보다 "어떻게 작성하는지 이해"에 있다.
- 각 starter는 실제 `BaseCheck` 메서드 이름과 반환 형식을 유지한다.

## 권장 매핑

- 단일 공통 UI 초기값: `script.py`
- `ssh` 또는 Rocky/Linux 계열: `rocky_ssh_starter.py`
- `winrm` 또는 Windows 계열: `windows_winrm_starter.py`
- `paramiko` 또는 Cisco IOS 계열: `cisco_ios_paramiko_starter.py`
