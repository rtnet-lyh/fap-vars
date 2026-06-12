# Inspection Register 작업 규칙

이 문서는 `inspection_cases_bundle/api_data/inspection_register/` 작업 흐름을 설명한다.

이 문서만 읽어도 다음 세션에서 사용자가 아래처럼 말했을 때 바로 작업할 수 있어야 한다.

```text
API로 서버에 등록해주세요.
```

## 목적

- 목적은 `api_data/os/<os>/*.md` 파일을 기준으로 내부 API 서버에 점검 항목을 등록하는 것이다.
- 등록 전에는 반드시 lookup API를 먼저 호출해 필요한 id 값을 조회해야 한다.
- 등록 API 호출은 `inspection_create.py`가 담당한다.

## 입력 파일

등록 작업의 기준 입력은 아래 파일들이다.

1. `api_data/os/<os>/<case_name>.md`
2. `api_data/api_context.md`

### 1. `api_data/os/<os>/<case_name>.md`

이 파일에서 아래 값을 읽는다.

- `type_name`
- `area_name`
- `category_name`
- `application_type`
- `application`
- `inspection_code`
- `inspection_name`
- `inspection_content`
- `inspection_command`
- `inspection_output`
- `description`
- `thresholds`
- `inspection_script`
- `is_required`

### 2. `api_data/api_context.md`

이 파일에서 아래 값을 읽는다.

- `SESSION_ID`
- `URL`
- `language`

이 값은 lookup API 호출과 create API 호출에 모두 사용한다.


## 표준 입력/출력 스키마

### `api_data/api_context.md`

`api_context.md`는 세션 전용 파일이 아니라 API 작업 전체의 context 파일이다. 아래 값은 현재 등록, 조회, fetch 계열 도구가 공통으로 사용하는 표준 값이다.

| section | 필수 여부 | 사용처 | 비고 |
| --- | --- | --- | --- |
| `URL` | 필수 | lookup, create, update, fetch | API 서버 base URL |
| `SESSION_ID` 또는 `JSESSIONID` | 필수 | lookup, create, update, fetch | 쿠키의 JSESSIONID 값으로 사용 |
| `language` | 선택 | lookup, create, update, fetch | 없으면 `ko-KR` 기본값 |
| `application_name` | fetch 필수 | fetch | `/data/inspection/items` 목록 filter |
| `type_name` | fetch 필수 | fetch | `/data/inspection/items` 목록 filter |

`item_id`, `item_ids`, `mapping_id`는 `api_context.md`에 넣지 않는다. fetch 흐름은 `/data/inspection/items` 목록 응답 row의 `item_id`, `mapping_id`를 사용해 상세 API를 조회한다.

### `api_data/os/**/*.md`

`api_data/os` Markdown의 표준은 `inspection_create.py`의 `parse_api_data_md()`가 읽는 영문 section이다. 신규 등록, 수정, JSON 변환, raw/case 변환의 최종 Markdown은 이 형식을 따라야 한다.

| section | 필수 여부 | payload key |
| --- | --- | --- |
| `type_name` | 필수 | `type_name`, lookup `inspection_type` |
| `area_name` | 필수 | `area_name`, lookup `area` |
| `category_name` | 필수 | `category_name`, lookup `category` |
| `application_type` | 필수 | `application_type_name`, lookup `application_type` |
| `application` | 필수 | `application_name`, lookup `application` |
| `inspection_code` | 필수 | `inspection_code` |
| `is_required` | 필수 | `is_required` (`필수`이면 `1`, 그 외 `0`) |
| `inspection_name` | 필수 | `inspection_name` |
| `inspection_content` | 필수 | `inspection_content` |
| `inspection_command` | 필수 | `inspection_command` |
| `inspection_output` | 필수 | `inspection_output` |
| `description` | 필수 | `description` |
| `thresholds` | 선택 | `thresholds` |
| `inspection_script` | 필수 | `inspection_script` |

`type_name`과 `area_name`은 항상 고정값이라고 가정하지 않는다. raw/case 기반 생성 시에는 `generate_os_md_from_cases.py --type-name ... --area-name ...`로 조정할 수 있다.

### fetch JSON

`fetch_inspection_details.py`의 JSON 출력은 서버 목록 row와 상세 API 응답을 병합한 배열이다. 각 원소는 이후 `generate_os_md_from_api_json.py`가 Markdown으로 변환할 수 있는 아래 key를 기준으로 한다.

| key | 출처 | 비고 |
| --- | --- | --- |
| `item_id` | 목록 row | 상세 조회 대상 |
| `mapping_id` | 목록 row | 상세 응답의 target mapping 선택 |
| `type_name` | 상세 `item` | Markdown `type_name` |
| `area_name` | 상세 `item` | Markdown `area_name` |
| `category_name` | 상세 `item` | output path segment 1 |
| `inspection_code` | 상세 `item` | Markdown `inspection_code` |
| `inspection_name` | 상세 `item` | Markdown `inspection_name` |
| `inspection_content` | 상세 `item` | Markdown `inspection_content` |
| `application_type_name` 또는 `application_type` | 상세 mapping 또는 fallback | output path segment 2 |
| `application_name` | 상세 mapping | output path segment 3 |
| `inspection_command` | 상세 mapping | Markdown `inspection_command` |
| `inspection_output` | 상세 mapping | Markdown `inspection_output` |
| `description` | 상세 mapping | Markdown `description` |
| `inspection_script` | 상세 mapping | Markdown `inspection_script` |
| `thresholds` | optional thresholds API | `--include-thresholds`일 때만 포함 |

### legacy Markdown parser

`inspection_md_parser.py`는 표준 `api_data/os` parser가 아니다. 한글 heading 기반 과거 문서를 migration/compatibility 목적으로 읽는 legacy parser이며, 표준 운영 플로우는 `inspection_create.py`의 `parse_api_data_md()`를 기준으로 한다.

## lookup 단계

등록 전에 반드시 `inspection_lookup.py`를 사용해 아래 값을 조회한다.

- `type_id`
- `area_id`
- `category_id`
- `application_type_id`
- `application_id`

lookup 결과는 최종적으로 아래 구조를 채운다.

```python
{
    "type_id": type_id,
    "type_name": inspection_type,
    "area_id": area_id,
    "area_name": area,
    "category_id": category_id,
    "category_name": category,
    "application_type_id": application_type_id,
    "application_type_name": application_type,
    "application_id": application_id,
    "application_name": application,
}
```

### lookup 실패 시 재시도 규칙

lookup 단계에서 특정 `*name` 값을 찾지 못하면 바로 종료하지 말고, 먼저 API가 반환한 가능한 값을 확인한 뒤 같은 의미의 서버 실제 값으로 한 번 더 재시도한다.

특히 `category_name`은 md 문서 값과 서버 lookup 값이 다를 수 있으므로 아래 순서로 처리한다.

1. md의 `category_name`으로 먼저 lookup을 시도한다.
2. 실패하면 오류 메시지의 `가능한 값: ...` 목록을 확인한다.
3. 같은 의미의 서버 실제 값이 있으면 그 값으로 다시 lookup 한다.
4. 재시도에 성공하면 그 값을 사용해 다음 create 단계로 진행한다.
5. 가능한 값 목록에도 대응되는 값이 없으면 그때 실패로 보고 중단한다.

대표 예시는 아래와 같다.

- `category_name=LOG` 로 실패하고 가능한 값이 `CPU, Cluster, DISK, MEMORY, Network, OS, 로그, 커널` 이면 `로그`로 다시 lookup 한다.
- `category_name=KERNAL` 로 실패하고 가능한 값이 `CPU, Cluster, DISK, MEMORY, Network, OS, 로그, 커널` 이면 `커널`로 다시 lookup 한다.

즉, 문서 값이 영문 대문자 분류여도 서버가 한글 분류 체계를 쓰고 있으면 가능한 값 기준으로 서버 값을 선택해 재조회해야 한다.

## create 단계

`inspection_create.py`는 아래 순서로 동작해야 한다.

1. `api_data/os/<os>/<case_name>.md`를 읽는다.
2. 공용 `api_data/api_context.md`를 읽는다.
3. `inspection_lookup.py`를 호출해 lookup id들을 가져온다.
4. md에서 읽은 나머지 값과 lookup id를 합쳐 payload를 만든다.
5. `/data/inspection/items`로 POST 요청을 보낸다.

## update 단계

이미 서버에 등록된 `api_data/os/<os>/*.md` 항목을 md 기준으로 수정할 때는 `inspection_update.py`를 사용한다.

`inspection_update.py`는 아래 순서로 동작한다.

1. `api_data/os/<os>/*.md` 또는 `--recursive` 지정 시 하위 `*.md`를 읽는다.
2. 공용 `api_data/api_context.md`를 읽어 `JSESSIONID`와 `Language` 쿠키를 설정한다.
3. `/data/inspection/items/search`를 `application/x-www-form-urlencoded` POST로 호출해 서버 항목 목록을 가져온다. 기본 `search_data`는 빈 문자열이며 전체 검색 형태로 조회한다.
4. 서버 응답에서 `inspection_code`와 `application_name`이 md의 `inspection_code`, `application`과 일치하는 항목을 찾는다.
5. 매칭된 서버 항목의 `id`, `item_id`, `mapping_id`, `cve_id`, `importance`, `application_family_id`, `application_version_id`를 보존한다.
6. md 값과 lookup id를 합쳐 PATCH payload를 만든다.
7. `/data/inspection/items`로 PATCH 요청을 보낸다.

PATCH payload는 기존 서버 식별자와 md 기준 값을 결합한다.

```python
{
    "id": existing["id"],
    "item_id": existing["item_id"],
    "mapping_id": existing["mapping_id"],
    "type_id": resolved["type_id"],
    "type_name": resolved["type_name"],
    "area_id": resolved["area_id"],
    "area_name": resolved["area_name"],
    "category_id": resolved["category_id"],
    "category_name": resolved["category_name"],
    "application_type_id": resolved["application_type_id"],
    "application_type_name": resolved["application_type_name"],
    "application_id": resolved["application_id"],
    "application_name": resolved["application_name"],
    "inspection_code": parsed["inspection_code"],
    "inspection_name": parsed["inspection_name"],
    "inspection_content": parsed["inspection_content"],
    "inspection_command": parsed["inspection_command"],
    "inspection_output": parsed["inspection_output"],
    "description": parsed["description"],
    "inspection_script": parsed["inspection_script"],
    "is_required": parsed["is_required"],
    "thresholds": parsed["thresholds"],
    "revision_num": revision_num,
    "is_fix": False,
}
```

서버에 없는 항목이 있으면 기본적으로 중단한다. 누락 항목을 먼저 생성한 뒤 수정까지 이어가야 하면 `--create-missing --execute`를 같이 사용한다.

## 진행 규칙

사용자가 `"API로 서버에 등록해주세요."`라고 하면 아래 순서로 진행한다.

1. 사용자가 기준으로 삼을 `api_data/os/<os>/<case_name>.md` 파일을 확인한다.
2. `api_data/api_context.md`가 있는지 확인한다.
3. `inspection_lookup.py`를 통해 id 조회가 정상 수행되는지 먼저 확인한다.
4. id 조회가 성공하면 `inspection_create.py`로 payload preview를 만들거나 바로 등록한다.
5. 등록 API 응답을 확인한다.
6. 성공/실패 결과를 사용자에게 간단히 보고한다.

사용자가 `"api_data/os/<os>/*.md 기준으로 서버 항목을 수정해주세요."`라고 하면 아래 순서로 진행한다.

1. `inspection_update.py --os <os>`로 dry-run을 먼저 실행해 매칭 결과를 확인한다.
2. `missing` 항목이 없으면 `inspection_update.py --os <os> --execute`로 PATCH 수정한다.
3. `missing` 항목이 있으면 사용자의 의도에 따라 `inspection_update.py --os <os> --create-missing --execute`로 누락 항목을 POST 생성한 뒤 PATCH 수정한다.
4. 실행 후 다시 `inspection_update.py --os <os>` dry-run을 실행해 `matched`, `missing`, payload 준비 상태를 검증한다.

## 중단 조건

아래 경우에는 다음 단계로 진행하지 말고 즉시 중단한다.

- md 파일에 lookup에 필요한 `*name` 값이 없을 때
- `api_context.md`에 `SESSION_ID` 또는 `URL` 값이 없을 때
- lookup API가 id를 반환하지 못하고, 가능한 값 기준 재시도도 실패할 때
- update 단계에서 `inspection_code + application_name` 기준 서버 항목이 여러 개 매칭될 때
- update 단계에서 서버 항목의 `id`, `item_id`, `mapping_id` 등 PATCH 필수 식별자가 없을 때
- 세션 오류, 위치 제한, 인증 실패 등으로 API 접근이 거부될 때

이 경우에는 어떤 값이 없는지 또는 어떤 API 단계에서 실패했는지 분명하게 알려준다.

예시:

- `type_name 값이 없습니다.`
- `SESSION_ID 값이 없습니다.`
- `category_name 값을 API에서 찾지 못했습니다.`
- `category_name=LOG 조회에 실패했고 가능한 값 [CPU, Cluster, DISK, MEMORY, Network, OS, 로그, 커널] 기준으로 로그로 재시도했으나 여전히 찾지 못했습니다.`
- `lookup API 호출은 되었지만 accessfromanotherlocation 오류로 중단합니다.`

## 성공 판정

아래 두 조건을 만족하면 등록 성공으로 본다.

1. lookup API가 필요한 모든 id를 정상 반환한다.
2. create API 응답이 성공 상태를 반환한다.

예시 성공 응답:

```python
{"status": "success", "message": None, "data": None}
```

## 현재 구현 기준

현재 구현은 아래와 같이 동작한다.

- `inspection_lookup.py`
  - `api_data/os/<os>/<case_name>.md`에서 lookup용 `*name` 값을 읽는다.
  - `api_data/api_context.md`에서 세션 정보를 읽는다.
  - 내부 lookup API를 호출해 id를 조회한다.
  - lookup 실패 시 가능한 값 목록을 확인해 같은 의미의 서버 실제 값으로 재시도할 수 있어야 한다.

- `inspection_create.py`
  - `api_data/os/<os>/<case_name>.md`를 직접 읽는다.
  - `inspection_lookup.py` 결과를 이용해 payload에 id를 연결한다.
  - `/data/inspection/items`로 POST 요청을 보낸다.

## 빠른 실행 예시

기준 md 파일이 아래일 때:

```text
/home/fap/projects/fap-vars/inspection_cases_bundle/api_data/os/solaris/solaris_memory_recognition_prtdiag_check.md
```

실행 흐름은 아래와 같다.

1. `inspection_lookup.py`로 id 조회
2. `inspection_create.py`로 payload 생성
3. `inspection_create.py`로 등록 API POST 실행

## 사용자 보고 방식

등록이 성공하면 아래처럼 짧게 보고한다.

- 어떤 md 파일로 진행했는지
- lookup id 조회가 성공했는지
- 등록 API 응답이 성공인지

등록이 실패하면 아래를 포함해 보고한다.

- 실패 단계
- 실패 원인
- 어떤 값 또는 어떤 API 응답 때문에 중단됐는지
- 재시도한 값이 있으면 어떤 값으로 다시 조회했는지

## 금지 사항

- lookup 없이 바로 create API를 호출하지 않는다.
- search API로 기존 서버 항목의 `id`, `item_id`, `mapping_id`를 확인하지 않고 PATCH를 호출하지 않는다.
- `api_context.md` 값을 하드코딩해 고정하지 않는다.
- md 값이 비어 있는데 임의 문자열로 대체하지 않는다.
- 실패했는데 계속 다음 단계로 진행하지 않는다.

## update 빠른 실행 예시

Solaris md 항목을 서버 기존 항목에 반영하기 전 dry-run:

```bash
python3 inspection_update.py --os solaris
```

Solaris md 항목을 실제 PATCH 수정:

```bash
python3 inspection_update.py --os solaris --execute
```

서버에 없는 항목을 먼저 생성한 뒤 전체 수정:

```bash
python3 inspection_update.py --os solaris --create-missing --execute
```

특정 코드만 확인 또는 수정:

```bash
python3 inspection_update.py --os solaris --code SVR-4-1
python3 inspection_update.py --os solaris --code SVR-4-1 --execute
```

## API 상세 수집 및 JSON 기반 Markdown 생성

기존 서버에 등록된 특정 계열의 상세 값을 내려받을 때는 `fetch_inspection_details.py`를 사용한다. 이 도구는 `api_data/api_context.md`의 `URL`, `SESSION_ID` 또는 `JSESSIONID`, `language`, `application_name`, `type_name`을 읽고 `/data/inspection/items` 목록 API를 조회한다. 목록 응답 row에는 상세 조회에 필요한 `item_id`와 `mapping_id`가 포함되어 있으므로 `api_context.md`에 `item_id`를 별도로 넣어 직접 상세 조회하지 않는다.

1. `/data/inspection/items` 목록 API를 `type_name`, `application_name` filter로 조회한다.
2. 각 row의 `item_id`, `mapping_id`로 `/data/inspection/items/{item_id}` 상세 API를 조회한다.
3. 상세 응답의 `mappings` 중 `mapping_id`가 일치하는 mapping에서 `application_name`, `inspection_command`, `inspection_output`, `description`, `inspection_script`를 가져온다.
4. 기본 출력은 `api_data/inspection_register/outputs/<application_name>_inspection_details.json`이다.
5. `--include-thresholds`를 지정한 경우에만 `/data/inspection/items/{item_id}/thresholds`도 추가 조회한다.

수집된 JSON을 `api_data/os/<category_name>/<application_type>/<application>/<case_name>.md`로 변환할 때는 `generate_os_md_from_api_json.py`를 사용한다. `application_type`은 JSON의 `application_type_name` 또는 `application_type`을 우선 사용하고, 없으면 CLI `--application-type` 값을 fallback으로 사용한다.

## `match_raw_data_commands.py`의 목적

이 도구는 등록/수정용 일반 플로우가 아니라, 서버 API에 이미 존재하는 점검 항목과 로컬 replay case를 명령어 기준으로 연결하기 위한 보조 매칭 도구다.

- 서버 쪽 입력: `fetch_inspection_details.py`와 같은 `/data/inspection/items` 목록 API 결과이며, `api_context.md`의 `type_name`, `application_name` filter로 가져온다.
- 서버 쪽 매칭 값: 목록 row의 `inspection_command`, `category_name`, `inspection_name`, `inspection_code`, `item_id`, `mapping_id`, `application_name`이다.
- 로컬 쪽 입력: 현재 구현 기준으로 `inspection_cases/**/raw_data.md` 파일이다.
- 로컬 쪽 매칭 값: raw 문서의 `영역`, `세부 점검항목`, `명령어`이다.
- 1차 매칭 키: 정규화한 `(inspection_command, category_name)`과 정규화한 `(명령어, 영역)`이다.

매칭 결과는 `sync_scripts_from_api.py`가 API의 `inspection_script`를 어떤 로컬 `script.py`에 역동기화할지 결정하는 데 사용한다. 새 raw data 정본인 `inspection_cases_bundle/raw_data/**/*.md` 기준으로 재편할 때는 이 도구의 raw 탐색 위치도 함께 바꿔야 한다.
