# Repository Guidelines

## 적용 범위와 상위 규칙

이 문서는 `inspection_cases_bundle/raw_data/` 아래의 원천 Markdown 자료에 적용된다. 저장소 루트 `AGENTS.md`와 `inspection_cases_bundle/AGENTS.md`도 함께 적용하며, raw data 파일을 다룰 때는 이 문서의 Markdown 작성 규칙을 우선한다.

이 디렉터리는 점검 케이스의 명령어, 대표 출력, 설명, 임계치, 판단기준을 사람이 읽을 수 있는 Markdown 파일로 관리한다. 원천 자료만 수정하는 요청이면 기본적으로 replay 케이스(`inspection_cases/`)나 runtime 파일을 만들지 않는다.

## 프로젝트 구조 및 모듈 구성

현재 원천 자료는 다음 경로에 분류되어 있다.

- `server/esxi/`, `server/hpux/`, `server/rocky/`, `server/windows/`: 서버 계열 원천 케이스
- `solaris/`: Solaris 원천 케이스. 현재 구조를 유지하고, 명시 요청 없이 `server/solaris/`로 이동하지 않는다.
- `network/cisco_ios/`, `network/nx_os/`: 네트워크 장비 원천 케이스
- `was/jeus/rocky/`: JEUS on Rocky 계열 원천 케이스
- `web/webtob/rocky/`: WebtoB on Rocky 계열 원천 케이스

새 파일은 대상 계열의 기존 위치와 이름 규칙을 따른다. 예: `server/rocky/rocky_memory_usage_free_check.md`, `web/webtob/rocky/webtob_process_cpu_usage_top_grep_check.md`.

## Markdown Schema

각 케이스 파일은 기존 한국어 heading 구조를 유지한다. 일반적으로 다음 heading을 사용한다.

- `# 영역`: `MEMORY`, `DISK`, `LOG` 같은 상위 분류
- `# 세부 점검항목` 또는 `# 세부 점검 항목`: 구체적인 점검 항목명
- `# 점검 내용`: 확인할 내용
- `# 구분`: 서버, 네트워크, WAS, WEB 등 점검 구분
- `# 명령어`: 실행 명령어. 예: `free`, `lsblk`, `dmesg`
- `# 출력 결과`: 대표 명령 출력
- `# 설명`: 운영자가 읽을 설명과 조치 권고
- `# 임계치`: 필요한 경우 threshold 변수명과 기본값
- `# 판단기준`: 판정 방식

기존 파일에 `# 출력 결과(성공)`, `# 출력 결과(실패)`, `# 명령어 - process_name 변수`처럼 변형 heading이 있으면 해당 파일의 의미를 보존한다. 전체 schema 변경 요청이 없다면 heading 이름을 대량 정규화하지 않는다.

## 빌드, 테스트, 개발 명령

이 raw data 디렉터리에는 별도 빌드 시스템이 없다. 저장소 루트에서 다음 명령으로 가볍게 검증한다.

```bash
rg '^# ' inspection_cases_bundle/raw_data/server/rocky
```

특정 파일 형식을 확인할 때:

```powershell
Get-Content -Encoding UTF8 inspection_cases_bundle/raw_data/server/rocky/rocky_memory_usage_free_check.md | Select-Object -First 120
```

편집 전후 변경 상태 확인:

```bash
git status --short
```

## 작성 스타일 및 이름 규칙

- UTF-8 Markdown을 사용한다.
- 기존 한국어 heading 구조와 명령 출력 포맷은 임의로 바꾸지 않는다.
- 표 형태의 명령 출력은 공백 정렬을 보존한다. 출력 모양 자체가 샘플 근거의 일부다.
- Rocky, Windows, HPUX, ESXi, WAS, WEB 계열의 새 파일은 기존처럼 lowercase snake case 파일명을 사용한다.
- 기존 Cisco IOS 원천처럼 한국어가 포함된 파일명 체계가 있는 경로에서는 가까운 기존 파일의 이름 규칙을 따른다. 대량 rename은 별도 요청이 있을 때만 한다.
- threshold key는 `min_available_memory_percent`처럼 안정적인 영문 snake case 식별자로 작성한다.

## 테스트 지침

자동 테스트 suite는 없다. 새 파일이나 큰 수정에는 다음을 확인한다.

- 필수 heading이 빠지지 않았는지
- 명령어와 출력 결과가 서로 대응하는지
- 설명과 판단기준이 실제 출력에서 확인 가능한 값에 근거하는지
- `# 임계치`에 적은 key가 replay 케이스를 만들 때 `case.json`과 `script.py`에서 그대로 사용할 수 있는지
- 관련 replay 케이스를 함께 수정했다면 `inspection_cases_bundle/AGENTS.md`의 replay 검증 명령을 실행했는지

문서만 수정한 경우 자동 테스트를 실행하지 않아도 되지만, 최종 응답에 문서 변경이라 테스트를 생략했음을 적는다.

## 커밋 및 Pull Request 지침

루트 `AGENTS.md`의 커밋/PR 규칙을 따른다. PR에는 변경된 원천 케이스, 영향 경로, rename 또는 삭제 파일을 명시해 의도한 교체와 실수로 인한 손실을 구분할 수 있게 한다. replay 케이스를 함께 갱신했다면 실행한 replay 명령과 갱신된 `result.json` 또는 `summary.json` 범위를 함께 적는다.

## Agent 전용 지침

관련 없는 working tree 변경을 되돌리지 않는다. 케이스를 추가할 때는 기존 Markdown schema를 우선 따르고, 명시 요청이 없는 한 runtime 또는 replay bundle 파일을 새로 만들지 않는다. `documents/`의 변환 전 자료와 이 디렉터리의 정본 Markdown이 충돌하면 사용자 요청 범위와 가까운 기존 raw data 파일을 우선 기준으로 삼는다.
