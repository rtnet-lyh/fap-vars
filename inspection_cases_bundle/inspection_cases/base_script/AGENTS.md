# Repository Guidelines

## 프로젝트 구조 및 모듈 구성

이 디렉터리는 단일 FAP 점검 replay 케이스이다. 표준 케이스 구성을 유지한다.

- `script.py`: 실제 점검 로직. `BaseCheck`를 상속하고 `CHECK_CLASS = Check`를 정의한다.
- `case.json`: replay 메타데이터, credential 구조, 점검 항목 정보, threshold 정의를 담는다.
- `replay.json`: replay 런타임이 사용하는 터미널 입출력 기록이다.
- `result.json`: replay 실행으로 생성되는 결과 파일이다. 가능하면 직접 수정하지 않는다.
- `outputs/`: 긴 stdout fixture를 분리해 저장할 때 사용한다.

`__pycache__/` 같은 생성 캐시 파일은 수정하지 않는다.

## 빌드, 테스트, 개발 명령

기본 실행 위치는 이 디렉터리이다.

```bash
python3 -m py_compile script.py
```

`script.py`의 Python 문법 오류를 빠르게 확인한다.

```bash
python3 ../../inspection_runtime/replay_cli.py .
```

현재 케이스를 replay하고 `result.json`을 갱신한다.

```bash
python3 ../../inspection_runtime/replay_cli.py ../base_script
```

`inspection_cases/base_script` 경로를 명시해 실행하는 동일한 replay 명령이다.

## 코딩 스타일 및 이름 규칙

Python 코드는 공백 4칸 들여쓰기를 사용한다. 함수, 변수, 파일명은 `snake_case`를 따른다. import는 파일 상단에 두고, 표준 라이브러리를 로컬 import보다 먼저 배치한다.

threshold를 추가할 때는 `case.json`의 threshold 이름과 `script.py`의 `self.get_threshold_var(...)` 키를 정확히 일치시킨다.

## `script.py` 작성 규칙

모든 점검 스크립트는 이 디렉터리의 `script.py` 패턴을 표준으로 따른다. 기본 골격은 `BaseCheck` 상속, `USE_HOST_CONNECTION`, `CHECK_CLASS = Check` 선언을 유지한다. 연결 방식은 `CONNECTION_METHOD`가 최우선이고, 없으면 실행 계정 형식(`connection_method`, `credential_type_name` 등)을 따른다. 둘 다 없으면 기본값은 `paramiko`이다.

- 명령 수행은 `run()`에서만 한다. threshold를 먼저 읽고, 신규 서버/장비 스크립트는 `_run_paramiko_commands(...)`, Windows 스크립트는 `_run_ps(...)`를 호출한다. `_ssh(...)`는 기존 스크립트 호환용으로만 유지한다.
- `replay.json`의 `matcher_value`는 `run()`에서 실제 실행하는 명령 문자열과 동일해야 한다.
- 파싱은 `parse_output(output)`에서만 처리한다. 이 함수는 raw output을 받아 측정값 dict인 `metrics`만 반환하고, 판정이나 메시지 문구를 만들지 않는다.
- 판정은 `evaluate(metrics, threshold...)`에서만 처리한다. 반환값은 `ok`, `warn`, `fail`, `excluded` 중 하나로 통일한다.
- 메시지 생성은 `build_result(metrics, threshold..., status)`에서만 처리한다. `message`, `results`, `criteria`를 담은 dict를 반환한다.
- `run()`은 threshold 로딩, 명령 수행, stdout 선택, `parse_output`, `evaluate`, `build_result`, `self.result(...)` 호출 순서로 조립한다.
- `run()`의 최종 반환은 반드시 `self.result(...)`만 사용한다. `self.ok(...)`, `self.fail(...)`, `self.warn(...)`, `self.excluded(...)` 같은 상태별 helper로 직접 반환하지 않는다.
- 연결 오류 판정은 precheck 단계에서 처리하므로 점검 스크립트 안에서 `self._is_connection_error(...)` 같은 연결 오류 helper를 호출하지 않는다.
- `rc` 값으로 성공, 실패, 제외 여부를 판단하지 않는다. 점검 판정은 명령 출력에서 파싱한 `metrics`와 threshold를 기준으로 `evaluate(...)`에서만 수행한다.

새 점검 로직을 추가하더라도 위 함수 경계를 유지한다. 추가 helper가 필요하면 파싱, 판정, 메시지 생성 중 어느 역할인지 분명히 드러나는 이름을 사용한다.

## 테스트 지침

이 케이스는 별도 unit test보다 replay로 검증한다. `script.py`, `case.json`, `replay.json`을 변경한 뒤에는 다음 명령을 실행한다.

```bash
python3 ../../inspection_runtime/replay_cli.py .
```

`result.json`에서 기대한 `status`, 충분한 `metrics`, 명확한 한국어 `message`가 생성됐는지 확인한다. `replay.json`을 바꾼 경우에는 `matcher_value`가 `script.py`에서 실제 실행하는 명령 문자열과 같은지 확인한다.

## 커밋 및 Pull Request 지침

최근 커밋은 `base_script 샘플코드 추가`, `git upload 3회차`처럼 짧고 직접적인 제목을 사용한다. 하나의 커밋에는 하나의 논리적 변경만 담는다.

PR에는 변경 범위가 script, replay fixture, 생성 result, sample metadata 중 어디인지 적는다. 실행한 replay 명령과 생략한 검증이 있다면 함께 남긴다.

## 보안 및 설정 주의사항

실제 운영 credential, 토큰, 호스트 비밀값, 비공개 운영 데이터를 추가하지 않는다. credential 값은 샘플 또는 placeholder로 유지하고, 민감한 터미널 입력은 `replay.json`에서 redacted 항목으로 기록한다.
