  # FAP 점검항목 SQLite Import/Export 재설계안

  ## Summary

  - 세 개의 샘플 SQLite를 기준으로 교환 포맷을 재정의한다.
      - 일상점검(상태점검)_202604151107.db
      - 취약점진단_202604151107.db
      - 테스트_202604151107.db
  - 세 파일은 모두 동일한 SQLite 스키마를 사용하므로, import/export는 단일 SQLite 교환 규격으로 통합한다.
  - 대신 데이터 품질 규칙은 meta.category_ty 기준의 유형별 검증으로 나눈다.
  - 확정 정책:
      - 표준 파일 형식은 SQLite 단일 파일
      - 한 파일 = 한 점검유형
      - import는 신규만 추가
      - 검증은 유형별 규칙 적용

  ## SQLite 규격

  - 테이블은 아래 두 개로 고정한다.
      - meta(key, value)
      - inspection_items(...)
  - meta는 최소 아래 키를 가진다.
      - exported_at
      - category_ty
      - row_count
      - 추가로 v1부터 schema_version=1을 넣는다.
  - inspection_items 컬럼은 현재 샘플과 동일하게 유지한다.
      - inspection_code, cve_id, type_name, category_name, area_name, inspection_name, inspection_content, importance, is_required, application_type_name, application_name,
        application_version, application_family_name, inspection_script, inspection_command, inspection_output, description
  - 파일 단위 규칙:
      - 모든 row의 type_name은 meta.category_ty와 일치해야 한다.
      - 서로 다른 점검유형이 한 파일에 섞이면 import 실패 처리한다.

  ## Import 설계

  - 신규 API를 추가한다.
      - POST /data/inspection/items/import-sqlite
      - GET /data/inspection/items/export-sqlite
      - 필요 시 POST /data/inspection/items/import-sqlite/validate
  - import 처리 흐름:
      1. 업로드 파일이 SQLite인지 확인
      2. 필수 테이블/컬럼/meta 확인
      3. row_count 검증
      4. category_ty 확인
      5. 유형별 필수값 검증
      6. 이름 기반으로 운영 DB 마스터 ID 해석/생성
      7. vars_inspection_item + vars_inspection_item_mapping insert
      8. 전체 성공 시 commit, 오류 시 rollback
  - import는 기존 데이터를 수정하지 않는다.
      - 기존 항목 merge/update/delete 없음
      - 항상 신규 item/mapping 생성만 수행
  - 이름 기반 해석 규칙은 서버에서 고정한다.
      - type_name -> vars_category_type
      - area_name -> vars_area
      - category_name + type/area -> vars_category
      - application_type_name -> vars_application_type
      - application_name -> vars_application
      - application_family_name -> vars_application_family
      - application_version -> vars_application_version
  - 존재하지 않는 마스터는 자동 생성한다.
  - import 결과 응답은 아래를 포함한다.
      - 총 row 수
      - 성공 건수
      - 실패 건수
      - 경고 건수
      - 신규 생성된 type/area/category/application/version 수
      - 실패 상세 목록

  ## 유형별 검증 규칙

  - 취약점진단
      - inspection_code 필수
      - inspection_name, category_name, area_name 필수
      - application_type_name은 사실상 필수로 취급
      - cve_id는 선택
      - inspection_script, inspection_command, inspection_output는 비어 있어도 허용
  - 일상점검(상태점검)
      - inspection_code 공란 허용
      - inspection_name, category_name, area_name, application_type_name 필수
      - inspection_script는 사실상 필수
      - application_name, application_version은 있으면 반영, 없으면 허용
  - 테스트
      - 개발/검증용 유형으로 취급
      - inspection_code 공란 허용
      - 최소한 inspection_name, category_name, area_name, application_type_name만 요구
      - 나머지는 느슨하게 허용
  - 공통 규칙
      - importance, is_required는 형변환 가능해야 함
      - 긴 텍스트(inspection_script, inspection_output, description)는 그대로 보존
      - 공백 문자열은 NULL 또는 빈값으로 정규화

  ## Export 설계

  - export는 운영 PostgreSQL에서 SQLite를 생성해 다운로드한다.
  - 파일은 항상 한 파일 한 점검유형으로 만든다.
      - 예: 취약점진단_YYYYMMDDHHMM.db
  - export 범위는 v1에서 아래만 포함한다.
      - 점검항목 본체
      - 점검항목 매핑
      - 스크립트/명령/출력/설명
  - v1 제외 범위:
      - threshold/기준치
      - 프로파일 매핑
      - 실행 이력/결과
      - 잠금 상태, 감사 이력 같은 운영 메타
  - export 시 row는 현재 UI/운영에서 조회되는 logical item+mapping 기준으로 1행씩 기록한다.

  ## UI 변경

  - tomcat/webapps/ROOT/resources/js/inspection/itemManagement.js:73의 업로드/다운로드 버튼을 실제 SQLite 흐름에 연결한다.
  - 기존 tomcat/webapps/ROOT/resources/js/popup/fileUploadModal.js:1는 구형 엑셀 bulk 업로드용이므로 역할을 분리한다.
      - 옵션 1: SQLite 전용 새 모달 추가
      - 옵션 2: 기존 모달을 SQLite 전용으로 교체하고 구형 엑셀은 숨김
  - v1 권장안은 새 SQLite 전용 모달 추가다.
      - 파일 형식 안내
      - 파일 메타 미리보기(category_ty, row_count)
      - validate 결과 표시
      - import 실행
  - 다운로드 버튼은 현재 선택한 점검유형 기준 export로 연결한다.

  ## Test Plan

  - 스키마 검증
      - 세 샘플 DB 모두 validate 성공
      - 테이블/컬럼 누락 DB는 실패
  - 유형별 검증
      - 취약점진단에서 코드 없는 row는 실패
      - 일상점검/테스트에서 코드 공란은 허용
  - 데이터 보존
      - 긴 inspection_script
      - 멀티라인 inspection_output
      - 따옴표/개행/한글 텍스트
  - 마스터 자동 생성
      - 새로운 area/category/application/version이 자동 생성되는지 확인
  - DB 적재
      - vars_inspection_item와 vars_inspection_item_mapping가 올바르게 분리 insert 되는지 확인
  - export round-trip
      - 운영 DB -> SQLite export -> validate -> import 재수행이 가능한지 확인
  - UI
      - 업로드/검증/실행/다운로드 흐름
      - 실패 상세와 경고 요약 표시

  ## Assumptions

  - 현재 세 샘플이 v1 공식 교환 포맷의 기준 데이터다.
  - 취약점진단은 코드 중심, 일상점검/테스트는 코드 비의존형 데이터로 취급한다.
  - v1은 “고객사 초기 구축용 이식”이 목적이므로 merge/update보다 안전한 신규 적재 우선으로 간다.
  - threshold와 profile까지 묶는 확장은 v2로 분리하는 것이 맞다.

