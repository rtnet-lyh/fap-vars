# AGENTS.md

이 저장소는 다른 OS에서도 바로 재생 가능한 점검 replay 번들이다. Codex CLI의 기본 목적은 현재 구조를 유지한 채 새 점검 케이스를 빠르게 추가하거나 기존 케이스를 수정하는 것이다.

## 목표

- 새 점검 요청이 오면 현재 번들 구조에 맞는 replay 케이스를 작성한다.
- 가능하면 `inspection_runtime/`은 건드리지 않고 `inspection_cases/` 아래에서 해결한다.
- 결과물은 사람이 읽기 쉽고 `python3 inspection_runtime/replay_cli.py ...`로 바로 재생 가능해야 한다.

## 저장소 구조

- `inspection_cases/`: 점검 케이스 모음
- `inspection_runtime/`: replay 실행 최소 런타임
- `README_BUNDLE.md`: 번들 목적과 실행 방법
- `inspection_cases/README.md`: 케이스 작성 규칙과 샘플 설명
- `raw_data/`: 점검 명령어, 출력결과, 판단근거 모음

새 점검 로직의 기본 위치는 `inspection_cases/<case_name>/` 이다.

## 기본 원칙

- 사용자가 "스크립트 만들어줘"라고만 말해도 이 저장소에서는 기본적으로 standalone shell보다 replay 케이스를 우선 고려한다.
- 사용자가 standalone shell 스크립트를 명시적으로 원할 때만 루트나 적절한 경로에 `.sh` 파일을 추가한다.
- replay 케이스를 만들 때는 기존 샘플과 같은 파일 세트를 맞춘다.
- `result.json`, `summary.json`은 생성 산출물이므로 가능하면 수동 편집하지 말고 재생 실행으로 갱신한다.
- 긴 명령 출력은 `replay.json`의 `stdout`에 직접 넣지 말고 `outputs/*.stdout` 파일로 분리한다.
- 임계치를 쓰는 경우 `item.threshold_list[].name` 과 `script.py`의 `get_threshold_var(...)` 키를 반드시 동일하게 맞춘다.
- `replay.json`의 `matcher_value`는 `script.py`가 실제 실행하는 명령 문자열과 동일해야 한다.
- `script.py`, `replacy_cli.py` 를 제외한 helpers, common, runner와 같은 파일은 수정하면 안된다.

## 케이스 디렉터리 표준 구성

각 케이스는 보통 아래 구조를 따른다.

```text
inspection_cases/<case_name>/
├── case.json
├── replay.json
├── result.json
├── script.py
└── outputs/
```

`outputs/`는 긴 stdout이 없으면 생략 가능하지만, 일반적으로 만드는 편이 안전하다.

## OS별 작성 규칙

### Linux / Cisco IOS

- `script.py`에서 `USE_HOST_CONNECTION = True`
- `CONNECTION_METHOD = 'ssh'`
- 명령 실행은 `_ssh("...")`
- 연결 실패는 `self._is_connection_error(rc, err)` 로 우선 처리
- 일반 명령 실패는 `rc != 0` 분기에서 처리

### Windows

- `CONNECTION_METHOD = 'winrm'`
- 필요 시 `WINRM_SHELL = 'powershell'`
- 명령 실행은 `_run_ps("...")`
- WinRM 환경 자체가 없을 수 있으므로 `self._is_not_applicable(rc, err)` 분기를 고려

## `script.py` 작성 규칙

`script.py`는 `BaseCheck`를 상속하는 Python 스크립트여야 한다.

최소 형태:

```python
# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh("command")

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={},
            thresholds={},
            reasons='판정 사유',
            message='점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
```

작성 시 반드시 지킬 것:

- 연결 실패, 명령 실패, 파싱 실패, 정책 실패를 구분해서 반환한다.
- 정상 반환에는 가능한 한 `metrics`, `thresholds`, `reasons`, `message`를 채운다.
- 판정 근거가 되는 값은 `metrics`에 남긴다.
- 사용한 임계치는 `thresholds`에 남긴다.
- 메시지는 사람이 결과를 읽었을 때 실패 이유를 바로 이해할 수 있게 쓴다.

## `case.json` 작성 규칙

- `inspection_code`는 케이스별로 유일해야 한다.
- 실제 핵심은 `credentials`, `item`, `item.threshold_list` 이다.
- `host`, `port`, `execution_id`, `host_id`, `job_id` 같은 메타 필드는 placeholder여도 된다.
- 새 케이스는 가장 가까운 기존 샘플을 복사해서 시작하는 것이 가장 안전하다.

권장 기준:

- Linux 계열은 `inspection_cases/linux_sample/` 또는 `inspection_cases/linux_df_sample/`
- Cisco IOS는 `inspection_cases/cisco_ios_sample/`
- Windows는 `inspection_cases/windows_sample/`

## `replay.json` 작성 규칙

- 배열 형태로 유지한다.
- 각 엔트리의 `matcher_type`은 특별한 이유가 없으면 `exact`를 사용한다.
- `matcher_value`는 실제 실행 명령과 완전히 같아야 한다.
- 긴 출력은 `stdout_file`을 사용한다.
- 여러 명령을 실행하면 스크립트 호출 순서대로 엔트리를 나열한다.

예시:

```json
[
  {
    "matcher_type": "exact",
    "matcher_value": "df -h",
    "rc": 0,
    "stdout_file": "outputs/df.stdout",
    "stderr": ""
  }
]
```

## Codex 작업 절차

새 점검 요청을 받으면 아래 순서로 처리한다.

1. 가장 가까운 샘플 케이스를 찾는다.
2. 새 디렉터리를 `inspection_cases/<case_name>/` 으로 만든다.
3. `case.json`을 샘플 기반으로 작성하고 필요한 threshold를 넣는다.
4. `script.py`를 작성한다.
5. `replay.json`과 필요 시 `outputs/*`를 작성한다.
6. `python3 inspection_runtime/replay_cli.py inspection_cases/<case_name>` 를 실행한다.
7. 생성된 `result.json` 내용을 확인해 상태, metrics, thresholds, message가 의도대로 나왔는지 검증한다.
8. 여러 케이스를 건드렸으면 `python3 inspection_runtime/replay_cli.py inspection_cases` 로 전체 집계도 갱신한다.

## 검증 명령

단일 케이스:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases/<case_name>
```

전체 케이스:

```bash
python3 inspection_runtime/replay_cli.py inspection_cases
```

추가 확인 포인트:

- `result.json.results[].status` 가 기대와 같은지
- `failed_items` 가 의도와 같은지
- `metrics` 에 판정 근거가 충분한지
- `thresholds` 에 실제 적용값이 남았는지
- `message`, `reasons`, `raw_output` 이 디버깅 가능한 수준인지

## 수정 범위 제한

다음 경우가 아니면 `inspection_runtime/` 수정은 피한다.

- 런타임 버그 때문에 어떤 케이스도 정상 재생되지 않는 경우
- 여러 케이스에 공통으로 필요한 헬퍼 추가가 명확한 경우
- 사용자가 런타임 자체 수정까지 명시적으로 요청한 경우

새 점검 하나를 추가하는 작업이라면 우선 `inspection_cases/` 안에서 끝내는 방향으로 작업한다.

## 완료 기준

- 새 케이스가 현재 디렉터리 구조를 따른다.
- `script.py`, `case.json`, `replay.json` 사이의 명령/threshold 이름이 일치한다.
- replay 실행으로 `result.json`이 갱신되었다.
- 필요하면 `summary.json`도 다시 생성되었다.
- 불필요한 런타임 수정이 없다.

## 빠른 판단 기준

- Linux CPU/메모리/파일/계정 점검: `linux_sample`, `linux_df_sample` 패턴에서 시작
- Cisco 장비 show 계열 점검: `cisco_ios_sample` 패턴에서 시작
- Windows PowerShell 점검: `windows_sample` 패턴에서 시작

모호하면 가장 가까운 샘플을 복사한 뒤 최소 변경으로 완성한다.
