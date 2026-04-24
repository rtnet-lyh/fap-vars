# Repository Guidelines

## 프로젝트 구조 및 모듈 구성

이 저장소는 점검 케이스 원천 데이터를 Markdown 파일로 관리한다. 원천 케이스는 `server/esxi/`, `server/hpux/`, `server/rocky/`, `server/windows/` 아래에 두며, 각 OS 계열 점검 항목마다 하나의 파일을 둔다. 예: `server/rocky/rocky_memory_usage_free_check.md`.

각 케이스 파일은 다음 한국어 heading 구조를 따른다.

- `# 영역`: `MEMORY`, `DISK`, `LOG` 같은 상위 분류
- `# 세부 점검항목`: 구체적인 점검 항목명
- `# 점검 내용`: 확인할 내용
- `# 명령어`: 실행 명령어. 예: `free`, `lsblk`, `dmesg`
- `# 출력 결과`: 대표 명령 출력
- `# 설명`: 운영자가 읽을 설명과 조치 권고
- `# 임계치`: 필요한 경우 threshold 변수명
- `# 판단기준`: 판정 방식

이 디렉터리에는 애플리케이션 소스 트리나 생성 asset 디렉터리가 없다. 새 원천 케이스는 OS 계열에 맞춰 `server/<os>/` 아래에 배치하고, Rocky Linux 항목은 `server/rocky/`에 둔다.

## 빌드, 테스트, 개발 명령

이 raw data 디렉터리에는 별도 빌드 시스템이 없다. 다음 명령으로 가볍게 검증한다.

```bash
rg '^# ' server/rocky
```

section heading을 나열해 누락되거나 일관되지 않은 구성을 찾는다.

```bash
git status --short
```

편집 전 rename, 삭제, 신규 파일 상태를 확인한다.

```bash
sed -n '1,120p' server/rocky/rocky_memory_usage_free_check.md
```

유사 파일을 추가하기 전 기존 케이스 형식을 확인한다.

## 작성 스타일 및 이름 규칙

UTF-8 Markdown을 사용한다. 전체 schema 변경 요청이 없다면 기존 한국어 heading을 그대로 유지한다. 파일명은 lowercase snake case로 작성한다.

```text
server/rocky/rocky_<영역>_<detail>_<command>_check.md
```

표 형태의 명령 출력은 공백 정렬을 보존한다. 출력 모양 자체가 샘플 근거의 일부다.

## 테스트 지침

이 디렉터리에는 자동 테스트 suite가 없다. 새 파일은 가까운 Rocky 샘플과 비교하고 필수 heading이 모두 있는지 수동 확인한다. Threshold key는 `min_available_memory_percent`처럼 안정적인 식별자로 작성한다.

## 커밋 및 Pull Request 지침

최근 커밋은 `patch fap-vars` 또는 변경 기능을 설명하는 짧은 한국어 요약을 사용한다. 커밋은 하나의 논리 변경에 집중한다. Pull Request에는 변경된 점검 케이스, 영향 경로, rename 또는 삭제 파일을 명시해 의도한 교체와 실수로 인한 손실을 구분할 수 있게 한다.

## Agent 전용 지침

관련 없는 working tree 변경을 되돌리지 않는다. 이 디렉터리에는 기존 `linux_*_sample.md` 이름에서 새 `rocky_*_check.md` 이름으로 바꾸는 작업이 진행 중일 수 있다. 케이스를 추가할 때는 기존 Markdown schema를 우선 따르고, 명시 요청이 없는 한 runtime 또는 replay bundle 파일을 새로 만들지 않는다.
