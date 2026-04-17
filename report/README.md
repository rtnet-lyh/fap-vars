## 목적
- vars-manager API에서 점검 결과를 조회해 엑셀 보고서를 생성한다.
- 표준 출력(stdout)은 다른 API가 파싱할 수 있도록 JSON만 출력한다.
- 보고서는 `요약` 시트와 호스트별 상세 시트로 구성한다.

## 구현 파일
- 실행 스크립트: `report/generate_report.py`
- 의존성 목록: `report/requirements.txt`
- 기본 테스트: `report/test_generate_report.py`

## API 접속 정보
- API 서버 정보는 `/fap/ansible/conf/fap.conf` 에서 읽는다.
- 사용 항목은 `[API_SERVER]` 섹션의 `API_URL`, `API_TOKEN` 이다.
- 인증 헤더는 `x-auth-token: Bearer <API_TOKEN>` 형식으로 전송한다.
- 리포트 데이터는 아래 2개 API를 사용한다.
  - `GET /api/system/getReportData/summary?jobId={job_id}&user_id={user_id}`
  - `GET /api/system/getReportData/detail?jobId={job_id}&user_id={user_id}`

## 실행 방법
1. 의존성을 설치한다.

```bash
python3 -m pip install -r report/requirements.txt
```

- Python 3.6/3.7 환경은 호환 버전의 `openpyxl 3.0.x`가 설치된다.
- Python 3.8 이상 환경은 `openpyxl 3.1+`를 사용한다.

2. `job_id`를 넘겨 실행한다.

```bash
python3 report/generate_report.py --job-id 464
```

추가 옵션:
- `--user-id`: 실행 사용자 ID를 결과 JSON에 포함
  - 생략 시 환경변수 `FAP_REPORT_USER_ID`, `FAP_USER_ID`, `REPORT_USER_ID`, `USER_ID` 순서로 대체 시도
- `--report-type`: 기본값 `default`
  - 지원 타입: `default`, `inspection`(default alias), `preventive`
- `--output-dir`: 보고서 저장 루트 지정
- `--output-name`: 파일명 prefix 지정, 기본값 `점검보고서`
- `--file-name`: 저장할 정확한 파일명 지정. 지정 시 timestamp를 붙이지 않음
- `--output-path`: `--file-name`과 함께 쓰면 저장 디렉터리 경로, 단독으로 쓰면 저장할 파일의 전체 경로
- `--mock-host-count`: DB 대신 mock 호스트 수만큼 가짜 데이터를 생성
- `--mock-items-per-host`: mock 모드에서 호스트당 상세 항목 수, 기본값 `3`

예시:

```bash
python3 report/generate_report.py --job-id 464 --user-id sysadm --output-path /tmp/reports --file-name custom_report.xlsx
```

`preventive` 보고서 예시:

```bash
python3 report/generate_report.py --job-id 464 --report-type preventive
```

DB 데이터 없이 분할 저장을 확인하려면:

```bash
python3 report/generate_report.py --job-id 999 --mock-host-count 260 --output-name 분할테스트
```

위 명령은 mock 호스트 260개를 생성하므로 여러 파일로 분할 저장된다.

## stdout JSON 계약
- `stdout`에는 아래 JSON 1개만 출력한다.
- 필수 키는 `result`, `report_path`, `msg` 이다.
- 추가 키로 `job_id`, `report_type`, `generated_at` 을 포함한다.
- `--user-id`를 전달하면 `user_id`도 함께 포함한다.
- 분할 저장이 발생하면 생성된 `.xlsx` 파일들을 `.zip`으로 압축하고, `report_path`는 `.zip` 경로를 반환한다.

성공 예시:

```json
{
  "result": "success",
  "report_path": "/abs/path/report/output/20260317/점검보고서_20260317_101500.xlsx",
  "msg": "report generated successfully",
  "job_id": 464,
  "user_id": "sysadm",
  "report_type": "default",
  "generated_at": "2026-03-17T10:15:00"
}
```

분할 저장 성공 예시:

```json
{
  "result": "success",
  "report_path": "/abs/path/report/output/20260317/점검보고서_20260317_101500.zip",
  "msg": "report generated successfully (2 files zipped)",
  "job_id": 999,
  "report_type": "default",
  "generated_at": "2026-03-17T10:15:00",
  "user_id": "sysadm"
}
```

실패 예시:

```json
{
  "result": "error",
  "report_path": null,
  "msg": "no summary rows found for job_id=464",
  "job_id": 464,
  "report_type": "default",
  "generated_at": "2026-03-17T10:15:00"
}
```

## 보고서 구조
### 1. 요약 시트
- 시트명: `요약`
- 문서 제목: `category_type_name`
- 요약 문구:
  - 점검점수: `score` 평균
  - 항목: `total_items` 평균
  - 양호: `vuln_items` 평균
  - 취약: `error_items` 평균
  - 미실행: `max(total_items - vuln_items - error_items, 0)` 평균  
- 작업번호: `job_id`
- 요약 테이블 컬럼:
  - 번호
  - 관리명
  - IP
  - 유형
  - 점수
  - 작업상태
  - 항목
  - 양호
  - 취약
  - 미실행
  - 시작시간
  - 종료시간
  - 소요시간
- `작업상태`: `host_status` 값을 표시하며 호스트별 작업 상태를 보여준다.
- `번호` 컬럼은 해당 호스트 상세 시트로 이동하는 링크를 건다.

### 분할 저장
- 한 파일의 최대 시트 수는 `250` 이다.
- `요약` 시트 1장을 포함하므로 상세 시트는 파일당 최대 `249`개까지 저장한다.
- 상세 시트가 이를 초과하면 자동으로 여러 파일로 분할 저장한다.
- 분할 파일명은 `{output-name}_{timestamp}_part01.xlsx` 형식이다.
- 분할된 각 파일은 해당 파일에 포함된 호스트의 요약 테이블과 상세 시트만 포함한다.
- 상단 요약 지표는 전체 작업 기준으로 동일하게 유지한다.

### 2. 호스트별 상세 시트
- 시트명은 관리명을 기준으로 생성한다.
- 엑셀 제약을 만족하도록 시트명 표준화 함수를 사용한다.
  - 최대 31자
  - 금지 문자 `\ / * ? : [ ]` 제거
  - 중복 시 suffix 추가
- 첫 줄은 `요약` 시트로 돌아가는 링크를 둔다.
- `A2`, `A3` 에는 호스트별 상세 제목과 요약 정보를 둔다.
- `default`, `inspection` 상세 테이블 컬럼:
  - 유형 `type_name`
  - 영역 `area_name`
  - 구분 `category_name`
  - 중요도 `importance` (`1 -> 하`, `2 -> 중`, `3 -> 상`)
  - 항목 `inspection_item_name`
  - 결과 `result_status`
  - 메세지 `message`
  - 상세 `raw_output`
- `preventive` 상세 시트는 점검항목 1개당 블록 테이블 1개를 생성한다.
  - 1행: 유형 `type_name`, 영역 `area_name`, 구분 `category_name`
  - 2행: 애플리케이션유형 `application_type_name`, 애플리케이션명 `application_name`, 버전 `application_version`
  - 3행: 점검결과 `result_status`, 중요도 `importance`
  - 4행: 점검항목 `inspection_item_name`
  - 5행: 명령어 `inspection_command`
  - 6행: 상세 `raw_output`
  - 7행: 메세지 `message`
  - 8행: 설명 `description`
  - 9행: 서비스 영향 유/무 `is_service_affect`
  - 10행: 조치내역 `action_content`
  - 각 블록 사이는 빈 줄 2개로 구분한다.

## 보고서 유형 확장
- 스크립트 내부에 report type registry를 두고 있다.
- 현재 등록된 타입은 `default`, `inspection`, `preventive` 이다.
- 새 유형이 필요하면 generator 클래스를 추가하고 alias를 registry에 등록한다.

## 리포트 데이터 API
### 요약 API
- `GET /api/system/getReportData/summary?jobId={job_id}&user_id={user_id}`
  - `user_id`를 직접 넘기지 않으면 스크립트가 위 환경변수들에서 대체 값을 먼저 찾는다.

### 상세 API
- `GET /api/system/getReportData/detail?jobId={job_id}&user_id={user_id}`
  - `user_id`를 직접 넘기지 않으면 스크립트가 위 환경변수들에서 대체 값을 먼저 찾는다.
  - `preventive` 에서 추가로 사용하는 상세 키:
    - `description`
    - `inspection_command`
    - `is_service_affect`
    - `action_content`
  - 위 키가 응답에 없으면 빈 문자열(`""`)로 처리한다.

## 예외 처리
- 실행 실패 시 `stdout JSON`의 `result`는 `error`, `report_path`는 `null` 이다.
- `msg`에는 예외 메시지만 넣는다.
