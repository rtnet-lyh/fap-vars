# Repository Guidelines

## 프로젝트 구조 및 모듈 구성

이 디렉터리는 점검 케이스 원천 데이터를 Markdown 파일로 관리한다. 현재 원천 자료는 다음 도메인 아래에 둔다.

- `server/`: `server/<os_family>/<platform>/` 구조로 Rocky, Windows, Solaris, HP-UX, ESXi 같은 서버 OS 계열 자료를 둔다.
- `network/`: Cisco IOS, NX-OS, Juniper Junos, Piolink PAS 같은 네트워크 장비 자료를 둔다.
- `was/`와 `web/`: JEUS, WebtoB처럼 애플리케이션 계열 자료를 둔다.
- `storage/`: Dell DDOS 등 스토리지 장비 자료를 둔다.
- `dbms/`: Oracle 등 DBMS 계열 자료를 둔다.
- `backup/`: Veritas NetBackup Appliance 등 백업 장비 또는 백업 솔루션 자료를 둔다.

새 원천 케이스는 `raw_data/<domain>/<application_type>/<application>/...` 아래에 배치한다. 예: `server/linux/rocky/rocky_memory_usage_free_check.md`, `network/nx_os/mds_c9148s/1_1_cpu.md`, `was/jeus/rocky/was_1_1_ps_cpu_chk.md`, `backup/veritas/netbackup_appliance_5240/1_1_catalog.md`.

각 케이스 파일은 가능한 한 다음 한국어 heading 구조를 따른다.

- `# 영역`: `MEMORY`, `DISK`, `LOG` 같은 상위 분류
- `# 세부 점검항목`: 구체적인 점검 항목명
- `# 점검 내용`: 확인할 내용
- `# 구분`: 필수, 선택 등 점검 구분
- `# 명령어`: 실행 명령어. 예: `free`, `lsblk`, `dmesg`
- `# 출력 결과`: 대표 명령 출력
- `# 설명`: 운영자가 읽을 설명과 조치 권고
- `# 임계치`: 필요한 경우 threshold 변수명
- `# 판단기준`: 판정 방식

이 디렉터리에는 애플리케이션 소스 트리나 생성 asset 디렉터리가 없다. 원천 Markdown만 수정하는 요청이면 runtime 또는 replay case를 새로 만들지 않는다.

## 빌드, 테스트, 개발 명령

이 raw data 디렉터리에는 별도 빌드 시스템이 없다. 다음 명령으로 가볍게 검증한다.

```bash
rg '^# ' server/linux/rocky
rg '^# ' network/nx_os/mds_c9148s
```

수정한 하위 경로의 section heading을 나열해 누락되거나 일관되지 않은 구성을 찾는다.

```bash
git status --short
```

편집 전 rename, 삭제, 신규 파일 상태를 확인한다.

```bash
sed -n '1,120p' server/linux/rocky/rocky_memory_usage_free_check.md
```

유사 파일을 추가하기 전 같은 도메인, 제품, OS의 기존 케이스 형식을 확인한다.

## 작성 스타일 및 이름 규칙

UTF-8 Markdown을 사용한다. 전체 schema 변경 요청이 없다면 기존 한국어 heading을 그대로 유지한다. 파일명은 같은 도메인, 제품, OS의 기존 패턴을 우선 따른다.

Rocky 서버 계열 파일은 lowercase snake case로 작성한다.

```text
server/linux/rocky/rocky_<영역>_<detail>_<command>_check.md
```

다른 도메인에는 `1_1_cpu.md`, `was_1_1_ps_cpu_chk.md`, `cisco_ios_자원사용률점검_CPU사용률.md`처럼 기존 파일명 패턴이 섞여 있으므로, 명시적인 rename 요청이 없으면 기존 패턴을 유지한다.

표 형태의 명령 출력은 공백 정렬을 보존한다. 출력 모양 자체가 샘플 근거의 일부다.

## 테스트 지침

이 디렉터리에는 자동 테스트 suite가 없다. 새 파일은 가까운 같은 도메인, 제품, OS 샘플과 비교하고 필수 heading이 모두 있는지 수동 확인한다. Threshold key는 `min_available_memory_percent`처럼 안정적인 식별자로 작성한다.

## 커밋 및 Pull Request 지침

최근 커밋은 `patch fap-vars` 또는 변경 기능을 설명하는 짧은 한국어 요약을 사용한다. 커밋은 하나의 논리 변경에 집중한다. Pull Request에는 변경된 점검 케이스, 영향 경로, rename 또는 삭제 파일을 명시해 의도한 교체와 실수로 인한 손실을 구분할 수 있게 한다.

## Agent 전용 지침

관련 없는 working tree 변경을 되돌리지 않는다. `server/linux/rocky/`에는 기존 `linux_*_sample.md` 이름에서 새 `rocky_*_check.md` 이름으로 바꾸는 작업이 진행 중일 수 있다. 다른 도메인은 같은 제품 또는 장비 계열의 기존 Markdown schema와 파일명 패턴을 우선 따른다. 명시 요청이 없는 한 runtime 또는 replay bundle 파일을 새로 만들지 않는다.
