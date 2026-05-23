# Repository Guidelines

## 프로젝트 구조 및 모듈 구성

이 저장소의 주요 작업 영역은 네 곳이다.

- `report/`: Python 기반 엑셀 점검 보고서 생성기. 실행 스크립트는 `report/generate_report.py`, 의존성은 `report/requirements.txt`, 테스트는 `report/test_generate_report.py`에 있다. 생성 보고서는 `report/output/` 아래에 저장된다.
- `credential_sync/`: FAP DB의 호스트 계정 정보를 VARS DB의 애플리케이션 계정 정보로 동기화하는 CLI. 실행 스크립트는 `credential_sync/sync_credentials.py`, 설정 예시는 `credential_sync/sample_config.yml`, 테스트는 `credential_sync/test_sync_credentials.py`에 있다.
- `mgmt_password/`: 호스트 엑셀 파일의 `password`, `become_password` 값을 규칙 기반으로 일괄 갱신하는 도구. 실행 스크립트는 `mgmt_password/update_host_passwords.py`, 설정 예시는 `mgmt_password/sample_rules.json`, 테스트는 `mgmt_password/test_update_host_passwords.py`에 있다.
- `inspection_cases_bundle/`: 점검 케이스 replay 번들. 런타임 코드는 `inspection_cases_bundle/inspection_runtime/`, 케이스 데이터는 `inspection_cases_bundle/inspection_cases/`, 원천 Markdown 자료는 `inspection_cases_bundle/raw_data/`에 있다.

`inspection_cases_bundle/` 하위 트리를 수정할 때는 `inspection_cases_bundle/AGENTS.md`와 `inspection_cases_bundle/raw_data/AGENTS.md`의 세부 규칙을 우선 따른다. `documents/`는 정부 지침, 데이터 구조, 변환 전후 샘플, 스크립트 산출물 등 참고 자료 성격이 강하므로 명시 요청이 없으면 일반적인 수정 대상에서 제외한다. `*.zip`, `*.tar.gz`, 생성된 엑셀 파일은 산출물로 보고 불필요하게 갱신하지 않는다.

## 빌드, 테스트, 개발 명령

- `python3 -m pip install -r report/requirements.txt`: 보고서 생성기 의존성을 설치한다.
- `python3 -m unittest report.test_generate_report`: 보고서 생성기 테스트를 실행한다.
- `python3 report/generate_report.py --job-id 464 --mock-host-count 10`: 실DB 없이 mock 데이터로 보고서 생성을 점검한다.
- `python3 -m pip install -r credential_sync/requirements.txt`: 계정 동기화 도구 의존성을 설치한다.
- `python3 -m unittest credential_sync.test_sync_credentials`: 계정 동기화 테스트를 실행한다.
- `python3 credential_sync/sync_credentials.py --config credential_sync/sample_config.yml`: FAP -> VARS 계정 동기화를 dry-run으로 점검한다.
- `python3 credential_sync/sync_credentials.py --config credential_sync/sample_config.yml --apply`: 계정 동기화를 실제 DB에 반영한다. 사용자가 명시적으로 요청한 경우에만 실행한다.
- `python3 -m unittest mgmt_password.test_update_host_passwords`: 호스트 비밀번호 갱신 도구 테스트를 실행한다.
- `python3 mgmt_password/update_host_passwords.py --config mgmt_password/sample_rules.json`: 샘플 규칙으로 호스트 엑셀 갱신을 실행한다.
- `python3 inspection_cases_bundle/inspection_runtime/replay_cli.py inspection_cases_bundle/inspection_cases/<case_name>`: 단일 점검 케이스를 재생한다.
- `python3 inspection_cases_bundle/inspection_runtime/replay_cli.py inspection_cases_bundle/inspection_cases`: 케이스 변경 후 전체 요약 결과를 다시 생성한다.

## 코딩 스타일 및 이름 규칙

Python 코드는 공백 4칸 들여쓰기를 사용하고, import는 표준 라이브러리를 우선 배치하며, 함수·변수·파일명은 `snake_case`를 따른다. 기존 코드가 타입 힌트를 사용하므로 새 helper와 테스트도 같은 스타일로 작성한다.

설정 파일은 용도에 맞게 `credential_sync`는 UTF-8 YAML, `mgmt_password`는 UTF-8 JSON을 사용한다. 실제 DB 접속 정보, 토큰, 운영 비밀번호는 샘플 파일이나 커밋 대상 문서에 넣지 않는다.

원천 점검 자료는 UTF-8 Markdown으로 유지하고, `rocky_memory_usage_free_check.md`처럼 소문자 snake case 파일명을 사용한다. 기존 한국어 heading 구조와 명령 출력 포맷은 임의로 바꾸지 않는다.

## 테스트 지침

Python 모듈을 수정할 때는 관련 `unittest`를 추가하거나 갱신한다.

- `report/` 변경: `python3 -m unittest report.test_generate_report`
- `credential_sync/` 변경: `python3 -m unittest credential_sync.test_sync_credentials`
- `mgmt_password/` 변경: `python3 -m unittest mgmt_password.test_update_host_passwords`

DB, API, 엑셀 원본 파일에 의존하는 흐름은 가능한 한 helper 단위 테스트와 mock 데이터로 검증한다. 운영 DB에 쓰는 명령(`--apply`)이나 실제 비밀번호 파일 갱신은 사용자가 명시적으로 요청한 경우에만 실행한다.

replay 번들을 수정했다면 `replay_cli.py`를 다시 실행해 `result.json`과 `summary.json`이 의도대로 재생성되는지 확인한다. 이 파일들은 생성 산출물이므로 가능하면 수동 편집하지 않는다.

문서만 수정한 경우에는 자동 테스트가 필수는 아니지만, 영향 경로와 실행하지 않은 검증을 최종 응답에 명확히 적는다.

## 커밋 및 Pull Request 지침

최근 커밋 메시지는 `patch fap-vars`, `레드마인 등록 기능 수정`처럼 짧고 직접적인 제목을 사용한다. 커밋은 하나의 논리적 변경만 담는 것이 좋다.

PR에는 변경 범위가 `report/`, `credential_sync/`, `mgmt_password/`, bundle runtime, raw data 중 어디인지 명확히 적고, 실행한 검증 명령을 함께 남긴다. 생성 파일, 엑셀 산출물, replay 결과, 케이스 rename이 포함되면 의도된 변경임을 설명해 리뷰어가 산출물 갱신과 불필요한 잡음을 구분할 수 있게 한다.

## Agent 전용 지침

작업 전 `git status --short`로 기존 변경을 확인하고, 사용자가 만든 변경을 되돌리지 않는다. 실제 운영 데이터, DB 쓰기, credential 갱신, 대량 산출물 재생성은 요청 범위를 다시 확인한 뒤 최소 범위로 수행한다. 문서와 샘플을 갱신할 때도 비밀값이 포함되지 않았는지 확인한다.
