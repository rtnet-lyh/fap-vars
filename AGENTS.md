# Repository Guidelines

## 프로젝트 구조 및 모듈 구성

이 저장소의 주요 작업 영역은 두 곳이다. `report/`에는 Python 기반 엑셀 보고서 생성기가 있으며, 실행 스크립트는 `report/generate_report.py`, 의존성은 `report/requirements.txt`, 테스트는 `report/test_generate_report.py`에 있다. 생성된 보고서는 `report/output/` 아래에 저장된다.

`inspection_cases_bundle/`은 점검 케이스 재생용 번들이다. 런타임 코드는 `inspection_cases_bundle/inspection_runtime/`, 케이스 데이터는 `inspection_cases_bundle/inspection_cases/`, 원천 Markdown 자료는 `inspection_cases_bundle/raw_data/`에 있다. 이 하위 트리를 수정할 때는 `inspection_cases_bundle/AGENTS.md`와 `inspection_cases_bundle/raw_data/AGENTS.md`의 세부 규칙을 우선 따른다. `documents/`와 `*.tar.gz`는 참고 자료 또는 패키징 산출물로 보고, 일반적인 수정 대상에서는 제외한다.

## 빌드, 테스트, 개발 명령

- `python3 -m pip install -r report/requirements.txt`: 보고서 생성기 의존성을 설치한다.
- `python3 -m unittest report.test_generate_report`: 보고서 생성기 테스트를 실행한다.
- `python3 report/generate_report.py --job-id 464 --mock-host-count 10`: 실DB 없이 mock 데이터로 보고서 생성을 점검한다.
- `python3 inspection_cases_bundle/inspection_runtime/replay_cli.py inspection_cases_bundle/inspection_cases/<case_name>`: 단일 점검 케이스를 재생한다.
- `python3 inspection_cases_bundle/inspection_runtime/replay_cli.py inspection_cases_bundle/inspection_cases`: 케이스 변경 후 전체 요약 결과를 다시 생성한다.

## 코딩 스타일 및 이름 규칙

Python 코드는 공백 4칸 들여쓰기를 사용하고, import는 표준 라이브러리를 우선 배치하며, 함수·변수·파일명은 `snake_case`를 따른다. 테스트를 확장할 때는 `report/test_generate_report.py`의 보조 함수 작성 방식과 타입 힌트 스타일을 맞춘다. 원천 점검 자료는 UTF-8 Markdown으로 유지하고, `rocky_memory_usage_free_check.md`처럼 소문자 snake case 파일명을 사용한다. 기존 한국어 heading 구조와 명령 출력 포맷은 임의로 바꾸지 않는다.

## 테스트 지침

`report/`를 수정할 때는 `unittest` 기반 테스트를 추가하거나 갱신한다. 새 테스트는 가능하면 `report/test_generate_report.py` 또는 인접한 `test_*.py` 파일에 둔다. 라이브 API 호출보다 재현 가능한 helper 단위 테스트를 우선한다. replay 번들을 수정했다면 `replay_cli.py`를 다시 실행해 `result.json`과 `summary.json`이 의도대로 재생성되는지 확인하고, 이 파일들을 수동으로 편집하지 않는다.

## 커밋 및 Pull Request 지침

최근 커밋 메시지는 `patch fap-vars`, `레드마인 등록 기능 수정`처럼 짧고 직접적인 제목을 사용한다. 커밋은 하나의 논리적 변경만 담는 것이 좋다. PR에는 변경 범위가 `report/`, bundle runtime, raw data 중 어디인지 명확히 적고, 실행한 검증 명령을 함께 남긴다. 생성 파일이나 케이스 rename이 포함되면 의도된 변경임을 설명해 리뷰어가 산출물 갱신과 불필요한 잡음을 구분할 수 있게 한다.
