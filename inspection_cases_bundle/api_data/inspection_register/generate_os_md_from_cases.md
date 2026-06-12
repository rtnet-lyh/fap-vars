# generate_os_md_from_cases 운영 계획

## 목적

`generate_os_md_from_cases.py`는 `inspection_cases_bundle/raw_data`의 원천 Markdown과 `inspection_cases_bundle/inspection_cases`의 replay 케이스 `script.py`를 결합해 API 등록용 Markdown을 `inspection_cases_bundle/api_data/os` 아래에 생성하기 위한 범용 도구입니다.

이 문서는 도구 구현 전 기준 문서입니다. Codex CLI 또는 작업자가 후속 Phase에서 generator를 작성하거나 실행할 때 아래 규칙을 우선 확인합니다.

## 기준 예시

출력 Markdown의 section 구성과 `thresholds`, `inspection_script` 배치 방식은 다음 파일을 기준 예시로 사용합니다.

```text
inspection_cases_bundle/api_data/os/_reference/example.md
```

기준 예시는 reference 전용이며, generator의 입력 또는 출력 대상이 아닙니다.

## 표준 path convention

`raw_data`, `inspection_cases`, `api_data/os`는 다음 논리 구조를 기준으로 맞춥니다.

```text
<category_name>/<application_type>/<application>/<case>
```

각 segment의 의미는 다음과 같습니다.

| Segment | Metadata field | 설명 |
| --- | --- | --- |
| `category_name` | `category_name` | `server`, `network`, `was`, `web`, `storage`, `dbms`, `backup` 같은 최상위 분류 |
| `application_type` | `application_type` | OS family, 제품 family, 장비 OS, 솔루션 family 등 category 하위의 1차 분류 |
| `application` | `application` | 실제 OS, 제품, 장비 모델, 실행 환경 등 API 등록 대상 애플리케이션명 |
| `case` | 파일명 또는 케이스 디렉터리명 | raw Markdown 파일명에서 `.md`를 제거한 값과 대응되는 inspection case 디렉터리명 |

예시는 다음과 같습니다.

```text
raw_data/network/nx_os/mds_c9148s/1_1_cpu.md
inspection_cases/network/nx_os/mds_c9148s/1_1_cpu/script.py
api_data/os/network/nx_os/mds_c9148s/1_1_cpu.md
```

위 경로의 metadata는 다음과 같습니다.

```text
category_name: network
application_type: nx_os
application: mds_c9148s
```

## 서버 계열 표준 구조

서버 계열은 기존 1-depth platform 구조를 유지하지 않고, 다음 3-depth convention을 표준으로 사용합니다.

```text
server/unix/solaris
server/unix/hpux
server/linux/rocky
server/windows/windows2019
server/vmware/esxi
```

예시는 다음과 같습니다.

```text
raw_data/server/unix/solaris/solaris_cpu_usage_prstat_check.md
inspection_cases/server/unix/solaris/solaris_cpu_usage_prstat_check/script.py
api_data/os/server/unix/solaris/solaris_cpu_usage_prstat_check.md
```

위 경로의 metadata는 다음과 같습니다.

```text
category_name: server
application_type: unix
application: solaris
```

## 입력과 출력 경로

기본 경로는 다음과 같이 둡니다.

| 용도 | 기본 경로 |
| --- | --- |
| raw root | `inspection_cases_bundle/raw_data` |
| case root | `inspection_cases_bundle/inspection_cases` |
| output root | `inspection_cases_bundle/api_data/os` |
| report root | `inspection_cases_bundle/api_data/_reports` |
| reference root | `inspection_cases_bundle/api_data/os/_reference` |

## 생성 대상과 제외 대상

### 생성 대상

다음 조건을 모두 만족하는 raw Markdown만 API 등록용 Markdown으로 생성합니다.

1. `inspection_cases_bundle/raw_data` 아래의 `.md` 파일입니다.
2. path가 `<category_name>/<application_type>/<application>/<case>.md` 구조를 만족합니다.
3. 대응되는 `inspection_cases/.../<case>/script.py`가 존재합니다.
4. `참고` 디렉터리 아래 파일이 아닙니다.
5. `AGENTS.md`가 아닙니다.

### 제외 대상

다음 파일은 생성하지 않고 skip report에 기록하거나, 단순 제외 카운트로 집계합니다.

| 제외 조건 | 처리 |
| --- | --- |
| `AGENTS.md` | 생성하지 않음, excluded count에 기록 |
| path segment에 `참고` 포함 | 생성하지 않음, excluded count에 기록 |
| path depth 부족 | 생성하지 않음, skip report에 기록 |
| 대응 `script.py` 없음 | 생성하지 않음, skip report에 기록 |
| 기존 출력 파일 존재, `--overwrite` 없음 | 생성하지 않음, skip report에 기록 |
| raw Markdown parsing 실패 | 생성하지 않음, skip report에 기록 |

## script.py 매칭 규칙

raw Markdown과 replay script는 같은 relative path를 기준으로 우선 매칭합니다.

```text
raw_data/<category_name>/<application_type>/<application>/<case>.md
inspection_cases/<category_name>/<application_type>/<application>/<case>/script.py
```

예시는 다음과 같습니다.

```text
raw_data/server/linux/rocky/rocky_memory_usage_free_check.md
inspection_cases/server/linux/rocky/rocky_memory_usage_free_check/script.py
```

일부 기존 네트워크 케이스처럼 replay case 디렉터리에 `_check` suffix가 붙은 경우를 위해, exact match 실패 시 `<case>_check/script.py`도 fallback으로 확인합니다.

```text
raw_data/network/nx_os/mds_c9148s/1_1_cpu.md
inspection_cases/network/nx_os/mds_c9148s/1_1_cpu_check/script.py
```

raw 파일명과 replay case 이름이 설명 suffix까지 다르지만 같은 점검 번호를 포함하는 경우를 위해, exact 및 `_check` fallback 실패 시 말단 case 이름에서 첫 번째 숫자 키(`1_1`, `2_4` 등)를 추출해 같은 부모 아래의 단일 matching case도 확인합니다. backup처럼 raw path에 vendor segment가 있고 replay case parent에는 vendor segment가 없는 기존 구조를 위해 `<category>/<application>/` parent도 함께 확인합니다.

```text
raw_data/backup/veritas/netbackup_appliance_5240/1_1_catalog.md
inspection_cases/backup/netbackup_appliance_5240/nbu_1_1_catalog_backup_status_check/script.py
```

`script.py`가 없으면 출력 Markdown을 생성하지 않습니다. 이 파일은 skip report에 `missing_script` 사유로 기록합니다.

## raw Markdown heading 파싱 규칙

raw Markdown에서는 다음 heading을 우선 파싱합니다.

| raw heading | 출력 field |
| --- | --- |
| `# 영역` | 참고 정보. 기본 출력 field로 직접 쓰지 않음 |
| `# 세부 점검항목` | `inspection_name` |
| `# 점검 내용` | `inspection_content` |
| `# 구분` | `is_required` |
| `# 명령어` | `inspection_command` |
| `# 출력 결과` | `inspection_output` |
| `# 설명` | `description` |
| `# 임계치` | `thresholds` 후보 |
| `# 판단기준` | `description` 뒤에 함께 병합 |

`description`은 `# 설명` 본문 뒤에 `# 판단기준` 본문을 이어 붙여 생성합니다.

## case.json 사용 규칙

대응 case 디렉터리에 `case.json`이 있으면 다음 값을 우선 사용합니다.

| case.json source | 출력 field | 우선순위 |
| --- | --- | --- |
| `inspection_code` 또는 item 내부 inspection code | `inspection_code` | raw Markdown보다 우선 |
| `item.threshold_list` | `thresholds` | raw `# 임계치`보다 우선 |
| required 여부를 확인할 수 있는 field | `is_required` 후보 | raw `# 구분`이 비어 있을 때 사용 |

`case.json`이 없어도 `script.py`와 raw Markdown이 있으면 생성은 가능하지만, report에는 warning으로 남깁니다.

## 출력 Markdown section

출력 Markdown은 다음 section 순서를 사용합니다.

````text
# type_name

일상점검

# area_name

상태점검

# category_name

<category_name>

# application_type

<application_type>

# application

<application>

# inspection_code

<inspection_code>

# is_required

<is_required>

# inspection_name

<inspection_name>

# inspection_content

<inspection_content>

# inspection_command

```bash
<inspection_command>
```

# inspection_output

```text
<inspection_output>
```

# description

<description>

# thresholds

<thresholds>

# inspection_script

<script.py 전문>
````

`inspection_script`는 기준 예시와 같이 코드펜스로 감싸지 않고 `script.py` 전문을 그대로 붙입니다.

## metadata 매핑 규칙

| 출력 section | 값 | Source |
| --- | --- | --- |
| `type_name` | `일상점검` | 고정값 |
| `area_name` | `상태점검` | 고정값 |
| `category_name` | path segment 1 | `<category_name>` |
| `application_type` | path segment 2 | `<application_type>` |
| `application` | path segment 3 | `<application>` |
| `inspection_code` | `case.json` 우선 | 없으면 빈 값 또는 raw 후보 |
| `is_required` | raw `# 구분` 우선 | 없으면 `case.json` 후보 |
| `inspection_name` | raw `# 세부 점검항목` | raw Markdown |
| `inspection_content` | raw `# 점검 내용` | raw Markdown |
| `inspection_command` | raw `# 명령어` | raw Markdown |
| `inspection_output` | raw `# 출력 결과` | raw Markdown |
| `description` | raw `# 설명` + `# 판단기준` | raw Markdown |
| `thresholds` | `case.json` threshold 우선 | 없으면 raw `# 임계치` |
| `inspection_script` | 대응 `script.py` 전문 | replay case |

## thresholds 포맷

`thresholds`는 기준 예시와 유사한 JS object 스타일로 출력합니다. 표준 JSON 문자열로 강제하지 않습니다.

예시는 다음과 같습니다.

```text
[
    {id: null, key: "max_cpu_usage_percent", value: "70", sortOrder: 0}
,
{id: null, key: "failure_keywords", value: "", sortOrder: 1}
]
```

권장 우선순위는 다음과 같습니다.

1. `case.json`의 `item.threshold_list`
2. raw Markdown의 `# 임계치`
3. threshold 정보가 없으면 빈 배열 `[]`

## report 생성 규칙

생성 결과는 사람이 검토하기 쉬운 Markdown report와 자동 처리 가능한 JSON summary로 남깁니다.

```text
inspection_cases_bundle/api_data/_reports/skip_report.md
inspection_cases_bundle/api_data/_reports/summary.json
```

report에는 최소한 다음 항목을 포함합니다.

- 전체 raw Markdown 수
- 생성 성공 수
- 제외 수
- skip 수
- skip 사유별 개수
- `script.py` 미매칭 목록
- path depth 부족 목록
- 기존 출력 파일 존재 목록
- `case.json` 없음 warning 목록
- 생성된 출력 파일 목록

## 권장 CLI 옵션

후속 Phase에서 작성할 `generate_os_md_from_cases.py`는 다음 옵션을 지원하는 것을 권장합니다.

```text
--raw-root
--case-root
--output-root
--report-root
--dry-run
--overwrite
--report-only
```

기본 동작은 안전해야 합니다.

- `--dry-run`이면 출력 Markdown을 생성하지 않고 report만 생성하거나 콘솔 요약만 출력합니다.
- `--overwrite`가 없으면 기존 출력 파일을 덮어쓰지 않습니다.
- `--report-only`는 이미 계산된 결과 또는 dry-run 기준 report만 갱신하는 용도로 사용합니다.

## 실행 예시

### dry-run

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_cases.py --dry-run
```

### 실제 생성

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_cases.py
```

### 기존 출력 파일 덮어쓰기

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_cases.py --overwrite
```

## 검증 체크리스트

생성 후 다음을 확인합니다.

```bash
git status --short
find inspection_cases_bundle/api_data/os -type f -name '*.md' | sort
rg '^# inspection_script' inspection_cases_bundle/api_data/os
rg '^# type_name|^# area_name|^# category_name|^# application_type|^# application' inspection_cases_bundle/api_data/os
```

샘플 확인 대상은 다음을 권장합니다.

```text
api_data/os/server/unix/solaris/<case>.md
api_data/os/server/unix/hpux/<case>.md
api_data/os/server/linux/rocky/<case>.md
api_data/os/server/windows/windows2019/<case>.md
api_data/os/server/vmware/esxi/<case>.md
api_data/os/network/nx_os/<application>/<case>.md
```

## Codex 작업 시 주의사항

- 이 문서는 generator 구현 전 기준 문서입니다.
- generator 구현 전에는 `raw_data`와 `inspection_cases`를 자동 이동하지 않습니다.
- `inspection_runtime`은 이 작업 범위가 아니므로 수정하지 않습니다.
- `참고` 디렉터리와 `AGENTS.md`는 생성 대상에서 제외합니다.
- script 없는 raw Markdown은 임의로 빈 `inspection_script`를 만들지 말고 skip report에 남깁니다.
- 대량 생성 전에는 반드시 `--dry-run`으로 성공/skip 수를 먼저 확인합니다.
- replay 결과 파일인 `result.json`, `summary.json`은 이 문서 작성 또는 generator 문서화 단계에서 갱신하지 않습니다.
