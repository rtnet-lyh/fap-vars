# Inspection Register Workflow

이 문서는 `inspection_cases_bundle/api_data/inspection_register/` 도구를 Codex CLI가 혼동 없이 사용할 수 있도록 정리한 실행 지침입니다.

핵심 원칙은 다음과 같습니다.

1. **등록/수정 기준 문서는 `api_data/os/**/*.md`입니다.**
2. **API 접속 정보는 `api_data/api_context.md`만 우선 사용합니다.** `session.md`는 legacy fallback입니다.
3. **`--execute` 또는 `--write`가 없는 명령은 서버/파일에 쓰지 않는 검증 단계로 취급합니다.**
4. **live API 호출은 사용자가 명시적으로 요청한 경우에만 수행합니다.** 문서 정리, parser/generator 검증, fixture 테스트에서는 호출하지 않습니다.
5. **`type_name`, `area_name`, `application_type`은 고정값으로 가정하지 않습니다.** 문서 또는 API 응답 값을 우선 사용하고, CLI fallback은 명시된 경우에만 사용합니다.

---

## 1. 디렉터리와 역할

```text
inspection_cases_bundle/
├── raw_data/                         # 원천 Markdown 정본
├── inspection_cases/                 # replay case: case.json, script.py, replay.json
└── api_data/
    ├── api_context.md                # API 작업 context
    ├── os/                           # 등록/수정 기준 Markdown
    ├── _reports/                     # raw/case -> api_data/os 생성 리포트
    └── inspection_register/          # API 등록/조회/생성/동기화 도구
```

`api_data/os` Markdown의 표준 경로는 아래 형식입니다.

```text
inspection_cases_bundle/api_data/os/<category_name>/<application_type>/<application>/<case_name>.md
```

`raw_data` 원천 Markdown의 권장 경로는 아래 형식입니다.

```text
inspection_cases_bundle/raw_data/<category>/<application_type>/<application>/<case>.md
```

---

## 2. 표준 입력 스펙

### 2.1 `api_data/api_context.md`

`api_context.md`는 session 전용 파일이 아니라 API 작업 전체의 context 파일입니다.

필수/권장 값은 다음과 같습니다.

| section | 필수 여부 | 사용 도구 | 설명 |
| --- | --- | --- | --- |
| `URL` | 필수 | lookup/create/update/fetch | API base URL |
| `SESSION_ID` 또는 `JSESSIONID` | 필수 | lookup/create/update/fetch | 쿠키 `JSESSIONID` 값 |
| `language` | 권장 | lookup/create/update/fetch | 없으면 보통 `ko-KR` 기본값 |
| `application_name` | fetch/match/sync에서 필요 | fetch/match/sync | `/data/inspection/items` 목록 필터 또는 raw 필터 |
| `type_name` | fetch/match/sync에서 필요 | fetch/match/sync | `/data/inspection/items` 목록 필터 |

금지 사항:

- `item_id`, `item_ids`, `mapping_id`를 `api_context.md`에 추가하지 않습니다.
- 상세 조회가 필요하면 `/data/inspection/items` 목록 응답 row의 `item_id`, `mapping_id`를 사용합니다.

예시:

```md
# URL

https://example.internal

# JSESSIONID

xxxxxxxxxxxxxxxx

# language

ko-KR

# application_name

rocky

# type_name

정기점검
```

### 2.2 `api_data/os/**/*.md`

표준 parser는 `inspection_create.py`의 `parse_api_data_md()`입니다. 이 parser가 읽는 영문 section을 표준으로 사용합니다.

| section | 설명 |
| --- | --- |
| `type_name` | 점검 유형 이름 |
| `area_name` | 점검 분야 이름 |
| `category_name` | 점검 분류 이름 |
| `application_type` | 애플리케이션/OS 계열 이름 |
| `application` | 제품/애플리케이션 이름 |
| `inspection_code` | 점검 코드 |
| `is_required` | `필수`이면 required 처리 |
| `inspection_name` | 점검 항목명 |
| `inspection_content` | 점검 내용 |
| `inspection_command` | 점검 명령 |
| `inspection_output` | 예시 출력 |
| `description` | 설명 |
| `thresholds` | 선택: threshold 배열/텍스트 |
| `inspection_script` | 등록/수정할 Python script 내용 |

`inspection_md_parser.py`는 한글 heading 기반 과거 문서 호환용 legacy parser입니다. 신규 표준 플로우에서는 직접 사용하지 말고 `parse_api_data_md()` 기준으로 판단합니다.

### 2.3 fetch JSON

`fetch_inspection_details.py` 출력 JSON은 `/data/inspection/items` 목록 row와 상세 API 응답을 합친 데이터입니다. 이후 `generate_os_md_from_api_json.py`가 이 JSON을 `api_data/os` Markdown으로 변환합니다.

주요 key:

- 목록 row 기준: `item_id`, `mapping_id`, `inspection_code`, `inspection_name`, `category_name`, `application_name`, `inspection_command`
- 상세 응답 기준: `type_name`, `area_name`, `inspection_content`, `application_type_name` 또는 `application_type`, `inspection_output`, `description`, `inspection_script`
- `--include-thresholds`를 지정한 경우에만 `thresholds` 포함

---

## 3. Codex Agent 공통 작업 규칙

### 3.1 작업 전 확인

항상 먼저 확인합니다.

```bash
git status --short
```

다음 파일이 있는지 확인합니다.

```bash
python3 - <<'PY'
from pathlib import Path
for path in [
    Path('inspection_cases_bundle/api_data/api_context.md'),
    Path('inspection_cases_bundle/api_data/os'),
    Path('inspection_cases_bundle/api_data/inspection_register'),
]:
    print(path, 'OK' if path.exists() else 'MISSING')
PY
```

### 3.2 API 호출 안전 규칙

- `inspection_create.py`는 `--execute`가 없으면 POST하지 않습니다.
- `inspection_update.py`는 `--execute`가 없으면 PATCH/POST하지 않습니다.
- `sync_scripts_from_api.py`는 `--write`가 없으면 `script.py`를 덮어쓰지 않습니다.
- `fetch_inspection_details.py`, `match_raw_data_commands.py`, `sync_scripts_from_api.py`는 서버 조회가 필요하므로 사용자가 API 호출을 명시했을 때만 실행합니다.
- 운영 DB/API/credential에 쓰는 명령은 사용자 요청 범위 안에서만 실행합니다.

### 3.3 권장 검증 명령

코드 변경 후 최소 검증:

```bash
python3 -m unittest discover inspection_cases_bundle/api_data/inspection_register
python3 -m py_compile inspection_cases_bundle/api_data/inspection_register/*.py
git diff --check
```

---

## 4. 일반 등록 플로우: `api_data/os` Markdown → 서버 POST

대상 도구:

- `inspection_lookup.py`
- `inspection_create.py`

### Agent 지침

1. 기준 Markdown이 `api_data/os/**/*.md` 표준 section을 갖는지 확인합니다.
2. `api_context.md`에서 `URL`, `SESSION_ID`/`JSESSIONID`, `language`를 확인합니다.
3. lookup은 `type_name`, `area_name`, `category_name`, `application_type`, `application`으로 id를 찾습니다.
4. lookup 실패 시 가능한 값 목록이 있으면 의미가 같은 서버 값으로 재시도할 수 있습니다.
5. 등록은 반드시 preview 후 실행합니다.
6. 사용자가 실제 등록을 요청했을 때만 `--execute`를 붙입니다.

### 수동 실행

단일 파일 preview:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_create.py \
  --md-file inspection_cases_bundle/api_data/os/<category>/<application_type>/<application>/<case>.md
```

단일 파일 실제 POST:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_create.py \
  --md-file inspection_cases_bundle/api_data/os/<category>/<application_type>/<application>/<case>.md \
  --execute
```

디렉터리 preview:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_create.py \
  --md-dir inspection_cases_bundle/api_data/os/<category>/<application_type>/<application> \
  --recursive
```

특정 코드만 실제 POST:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_create.py \
  --md-dir inspection_cases_bundle/api_data/os/<category>/<application_type>/<application> \
  --recursive \
  --code <inspection_code> \
  --execute
```

---

## 5. 일반 수정 플로우: `api_data/os` Markdown → 서버 PATCH

대상 도구:

- `inspection_update.py`
- `inspection_lookup.py`
- 필요 시 `inspection_create.py`

### Agent 지침

1. update는 기본적으로 full-search입니다. `--search-data` 기본값은 빈 문자열입니다.
2. 서버 항목 매칭 기준은 `inspection_code + application_name`입니다.
3. 매칭된 서버 항목의 기존 식별자(`id`, `item_id`, `mapping_id` 등)는 보존합니다.
4. `--execute`가 없으면 PATCH하지 않고 preview/match만 수행합니다.
5. 서버에 없는 항목을 자동 생성하려면 사용자가 명시한 경우에만 `--create-missing --execute`를 사용합니다.
6. 중복 매칭 또는 PATCH 필수 식별자 누락 시 중단합니다.

### 수동 실행

OS 하위 폴더 preview:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_update.py \
  --os <category_or_os_folder> \
  --recursive
```

직접 디렉터리 preview:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_update.py \
  --md-dir inspection_cases_bundle/api_data/os/<category>/<application_type>/<application> \
  --recursive
```

특정 코드 PATCH:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_update.py \
  --md-dir inspection_cases_bundle/api_data/os/<category>/<application_type>/<application> \
  --recursive \
  --code <inspection_code> \
  --execute
```

누락 항목을 생성한 뒤 PATCH까지 진행해야 할 때:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_update.py \
  --md-dir inspection_cases_bundle/api_data/os/<category>/<application_type>/<application> \
  --recursive \
  --create-missing \
  --execute
```

---

## 6. raw/case 기반 Markdown 생성: `raw_data + inspection_cases` → `api_data/os`

대상 도구:

- `generate_os_md_from_cases.py`

### 목적

`inspection_cases_bundle/raw_data/**/*.md`, `inspection_cases/**/case.json`, `inspection_cases/**/script.py`를 조합해 표준 `api_data/os/**/*.md`를 생성합니다.

### Agent 지침

1. raw 정본은 가능하면 `inspection_cases_bundle/raw_data/<category>/<application_type>/<application>/<case>.md`를 사용합니다.
2. `script.py` 위치는 `resolve_case_dir()` 결과를 따릅니다.
3. report root는 `inspection_cases_bundle/api_data/_reports`입니다.
4. `type_name`, `area_name`은 고정값으로 가정하지 말고 필요한 경우 CLI로 지정합니다.
5. 먼저 `--dry-run`으로 생성/skip/warning 리포트를 확인합니다.
6. 실제 파일 생성은 사용자가 요청했을 때만 `--overwrite` 여부를 결정해 실행합니다.

### 수동 실행

Dry-run:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_cases.py \
  --raw-root inspection_cases_bundle/raw_data \
  --case-root inspection_cases_bundle/inspection_cases \
  --output-root inspection_cases_bundle/api_data/os \
  --report-root inspection_cases_bundle/api_data/_reports \
  --type-name '<type_name>' \
  --area-name '<area_name>' \
  --dry-run
```

실제 생성:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_cases.py \
  --raw-root inspection_cases_bundle/raw_data \
  --case-root inspection_cases_bundle/inspection_cases \
  --output-root inspection_cases_bundle/api_data/os \
  --report-root inspection_cases_bundle/api_data/_reports \
  --type-name '<type_name>' \
  --area-name '<area_name>'
```

기존 Markdown까지 덮어쓰기:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_cases.py \
  --raw-root inspection_cases_bundle/raw_data \
  --case-root inspection_cases_bundle/inspection_cases \
  --output-root inspection_cases_bundle/api_data/os \
  --report-root inspection_cases_bundle/api_data/_reports \
  --type-name '<type_name>' \
  --area-name '<area_name>' \
  --overwrite
```

---

## 7. API JSON 기반 Markdown 생성: fetch JSON → `api_data/os`

대상 도구:

- `fetch_inspection_details.py`
- `generate_os_md_from_api_json.py`

### Agent 지침

1. fetch는 사용자가 live API 조회를 명시했을 때만 실행합니다.
2. `fetch_inspection_details.py`는 `api_context.md`의 `URL`, `SESSION_ID`/`JSESSIONID`, `language`, `application_name`, `type_name`을 사용합니다.
3. `api_context.md`에서 `item_id`/`item_ids`를 읽지 않습니다.
4. 목록 API row의 `item_id`, `mapping_id`로 상세 API를 조회합니다.
5. thresholds는 `--include-thresholds`가 있을 때만 조회합니다.
6. JSON → Markdown 변환 시 `application_type_name` 또는 `application_type`을 우선 사용하고, 없을 때만 `--application-type` fallback을 사용합니다.
7. 생성 후 `parse_api_data_md()` round-trip 검증을 수행합니다.

### 수동 실행

Fetch:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/fetch_inspection_details.py \
  --context inspection_cases_bundle/api_data/api_context.md \
  --output inspection_cases_bundle/api_data/inspection_register/outputs/<application_name>_inspection_details.json
```

Threshold 포함 fetch:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/fetch_inspection_details.py \
  --context inspection_cases_bundle/api_data/api_context.md \
  --output inspection_cases_bundle/api_data/inspection_register/outputs/<application_name>_inspection_details.json \
  --include-thresholds
```

JSON → Markdown dry-run:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_api_json.py \
  --input inspection_cases_bundle/api_data/inspection_register/outputs/<application_name>_inspection_details.json \
  --output-root inspection_cases_bundle/api_data/os \
  --application-type '<fallback_application_type>' \
  --dry-run
```

실제 생성:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_api_json.py \
  --input inspection_cases_bundle/api_data/inspection_register/outputs/<application_name>_inspection_details.json \
  --output-root inspection_cases_bundle/api_data/os \
  --application-type '<fallback_application_type>'
```

덮어쓰기:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_api_json.py \
  --input inspection_cases_bundle/api_data/inspection_register/outputs/<application_name>_inspection_details.json \
  --output-root inspection_cases_bundle/api_data/os \
  --application-type '<fallback_application_type>' \
  --overwrite
```

---

## 8. API 기존 항목과 로컬 script.py 연결/역동기화 보조 플로우

대상 도구:

- `match_raw_data_commands.py`
- `sync_scripts_from_api.py`

이 플로우는 create/update 일반 등록 플로우가 아닙니다. 서버에 이미 존재하는 항목의 `inspection_command` 등을 기준으로 로컬 raw Markdown 및 `script.py`를 찾고, 필요 시 API의 `inspection_script`를 로컬 `script.py`로 역동기화하는 보조 도구입니다.

### 8.1 `match_raw_data_commands.py`

#### Agent 지침

1. 서버 입력은 `/data/inspection/items` 목록 API 결과입니다.
2. 서버 매칭 값은 `inspection_command`, `category_name`, `inspection_name`, `inspection_code`, `item_id`, `mapping_id`, `application_name`입니다.
3. 로컬 raw 입력은 canonical `inspection_cases_bundle/raw_data/**/*.md`를 우선 사용합니다.
4. `script.py` 위치는 `generate_os_md_from_cases.py`의 `resolve_case_dir()`와 같은 방식으로 찾습니다.
5. match 결과에는 반드시 `raw_data_path`, `script_path`, `match_strategy`가 있어야 합니다.
6. 결과 파일은 기본적으로 `inspection_cases_bundle/raw_data_command_matches.json`입니다.

#### 수동 실행

```bash
python3 inspection_cases_bundle/api_data/inspection_register/match_raw_data_commands.py
```

결과에서 확인할 항목:

- `matched_count`
- `duplicate_api_count`
- `unmatched_api_count`
- `unmatched_raw_count`
- 각 match의 `raw_data_path`, `script_path`, `match_strategy`

### 8.2 `sync_scripts_from_api.py`

#### Agent 지침

1. 먼저 match를 수행해 `script_path`가 정확한지 확인합니다.
2. sync는 match 결과의 `script_path`를 우선 사용합니다.
3. API 상세 응답의 `inspection_script`를 검증합니다.
4. `--write` 전 validation error가 있으면 중단합니다.
5. `--write` 시 기존 `script.py` backup과 `backup_manifest.json`을 남깁니다.
6. 사용자가 실제 역동기화를 요청하지 않으면 `--write`를 사용하지 않습니다.

#### 수동 실행

Validation report만 생성:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/sync_scripts_from_api.py \
  --report inspection_cases_bundle/api_script_sync_validation.json
```

실제 역동기화:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/sync_scripts_from_api.py \
  --report inspection_cases_bundle/api_script_sync_validation.json \
  --write
```

unmatched 항목이 있어도 validation error가 없으면 일부만 쓰기:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/sync_scripts_from_api.py \
  --report inspection_cases_bundle/api_script_sync_validation.json \
  --allow-partial \
  --write
```

명시 backup 위치 사용:

```bash
python3 inspection_cases_bundle/api_data/inspection_register/sync_scripts_from_api.py \
  --report inspection_cases_bundle/api_script_sync_validation.json \
  --backup-dir inspection_cases_bundle/api_data/inspection_register/backups/manual_sync \
  --write
```

---

## 9. 파일별 Agent 지침 요약

| 파일 | 역할 | Agent가 지켜야 할 점 | 수동 실행 성격 |
| --- | --- | --- | --- |
| `inspection_lookup.py` | 이름 기반 id lookup client | `api_context.md` 우선, `session.md`는 legacy fallback만 허용 | 직접 CLI보다는 create/update 내부에서 사용 |
| `inspection_create.py` | 표준 Markdown을 서버에 POST 등록 | `--execute` 없으면 POST 금지, 먼저 preview | `--md-file` 또는 `--md-dir`, `--recursive`, `--code`, `--execute` |
| `inspection_update.py` | 표준 Markdown 기준 서버 PATCH 수정 | 기본 full-search, 매칭 기준은 `inspection_code + application_name`, `--execute` 없으면 PATCH 금지 | `--os` 또는 `--md-dir`, `--recursive`, `--code`, `--execute` |
| `fetch_inspection_details.py` | 목록 API row 기반 상세 JSON fetch | `item_id(s)`를 context에서 읽지 않음, thresholds는 옵션 | `--context`, `--output`, `--include-thresholds` |
| `generate_os_md_from_api_json.py` | fetch JSON을 `api_data/os` Markdown으로 변환 | JSON의 `application_type_name/application_type` 우선, fallback은 옵션 | `--input`, `--output-root`, `--application-type`, `--dry-run`, `--overwrite` |
| `generate_os_md_from_cases.py` | raw/case/script 조합으로 `api_data/os` Markdown 생성 | report root는 `api_data/_reports`, `type_name/area_name`은 CLI로 조정 | `--raw-root`, `--case-root`, `--output-root`, `--report-root`, `--dry-run`, `--overwrite` |
| `inspection_md_parser.py` | legacy 한글 heading parser | 표준 parser로 사용하지 않음 | 필요 시 migration/compatibility 테스트에서만 사용 |
| `match_raw_data_commands.py` | API 목록 row와 raw/script 매칭 | create/update 아님, 결과에 `raw_data_path/script_path/match_strategy` 확인 | live API 목록 조회 후 JSON report 생성 |
| `sync_scripts_from_api.py` | API `inspection_script`를 local `script.py`로 역동기화 | `script_path` 우선, validation error면 `--write` 중단, backup manifest 필수 | `--report`, `--write`, `--allow-partial`, `--backup-dir` |

---

## 10. 중단 조건

아래 상황에서는 다음 단계로 진행하지 않고 사용자에게 원인과 필요한 값을 보고합니다.

- `api_context.md`에 `URL` 또는 `SESSION_ID`/`JSESSIONID`가 없음
- 표준 Markdown에 lookup 필수 값(`type_name`, `area_name`, `category_name`, `application_type`, `application`)이 없음
- lookup 결과가 없고 가능한 값 기반 재시도도 실패함
- update에서 `inspection_code + application_name` 기준 매칭이 0개 또는 여러 개임
- PATCH에 필요한 서버 식별자(`id`, `item_id`, `mapping_id`)가 없음
- sync validation error가 있음
- match 결과의 `script_path`가 비어 있거나 의도한 case가 아님
- 세션 만료, 인증 실패, 위치 제한 등으로 API 접근이 거부됨

보고 예시:

```text
중단: api_context.md에 JSESSIONID가 없습니다.
중단: category_name=LOG를 서버 lookup에서 찾지 못했습니다. 가능한 값: [CPU, 로그, 커널]
중단: CODE-001 + rocky 매칭 서버 항목이 2개입니다.
중단: sync validation error가 있어 --write를 실행하지 않았습니다.
```

---

## 11. 자주 쓰는 작업별 최소 명령

### Markdown parser/generator 테스트만 수행

```bash
python3 -m unittest discover inspection_cases_bundle/api_data/inspection_register
```

### raw/case에서 `api_data/os` Markdown 생성 가능성 확인

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_cases.py \
  --dry-run \
  --report-root inspection_cases_bundle/api_data/_reports
```

### 등록 payload preview

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_create.py \
  --md-file <api_data/os markdown path>
```

### 수정 매칭 preview

```bash
python3 inspection_cases_bundle/api_data/inspection_register/inspection_update.py \
  --md-dir <api_data/os directory> \
  --recursive
```

### API JSON을 Markdown으로 변환 dry-run

```bash
python3 inspection_cases_bundle/api_data/inspection_register/generate_os_md_from_api_json.py \
  --input <fetch output json> \
  --output-root inspection_cases_bundle/api_data/os \
  --dry-run
```
