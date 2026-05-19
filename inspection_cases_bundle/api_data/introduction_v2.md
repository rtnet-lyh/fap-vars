# API Data Markdown 작성 규칙 v2

이 문서는 `inspection_cases_bundle/api_data/os/<os>/*.md` 생성 전용 작업 지침이다.

이 문서를 기준으로 요청받았을 때 수행하는 일은 `api_data/os/<os>/*.md` 생성 또는 수정뿐이다.

다음은 이 문서의 범위가 아니다.

- `inspection_lookup.py` 실행
- `inspection_create.py` 실행
- 세션 사용 API 호출
- 서버 등록

서버 등록은 `api_data/inspection_register/REGISTER_WORKFLOW.md` 범위다.

## 작업 목표

- 결과 파일은 `api_data/os/<os>/<case_name>.md` 형식으로 만든다.
- 결과 파일의 키 이름과 순서는 반드시 `api_data/os/<os>/참고/example.md`와 동일해야 한다.
- 값은 `api_data/os/<os>/참고/inspection.md`, `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`, `inspection_cases/<zone>/<os>/<case_name>/script.py`에서 가져온다.

## 입력 자료

1. `api_data/os/<os>/참고/example.md`
2. `api_data/os/<os>/참고/inspection.md`
3. `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`
4. `inspection_cases/<zone>/<os>/<case_name>/script.py`

## 케이스 찾기 규칙

- `<zone>`은 고정값이 아니다.
- `inspection_cases/` 아래 zone 폴더를 순회하면서 원하는 `<os>` 폴더를 찾는다.
- 결과 파일명은 이미 존재하는 케이스 디렉터리명 `case_name`과 동일해야 한다.
- 케이스명 규칙은 `<application>_<category_name>_<inspection_name(english)>_<command>`이며, 실제 생성 파일명은 대응하는 `case_name`을 그대로 사용한다.

예시:

- `inspection_cases/server/solaris/solaris_cluster_daemon_scstat_check/`
- 결과 파일: `api_data/os/solaris/solaris_cluster_daemon_scstat_check.md`

## 필드 매핑

- `type_name`: `api_data/os/<os>/참고/example.md`
- `area_name`: `api_data/os/<os>/참고/example.md`
- `category_name`: `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `영역`
- `application_type`: `api_data/os/<os>/참고/example.md`
- `application`: `api_data/os/<os>/참고/example.md`
- `inspection_code`: `inspection.md`에서 `inspection_name`과 일치하는 항목 번호를 찾아 `SVR-x-y` 형식으로 변환
- `is_required`: `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 필수 여부, 없으면 기본값 `필수`
- `inspection_name`: `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `세부 점검항목`
- `inspection_content`: `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `점검 내용`
- `inspection_command`: `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `명령어`
- `inspection_output`: `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `출력 결과`
- `description`: `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `설명`과 `판단기준`을 합친 값
- `thresholds`: `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `임계치`
- `inspection_script`: `inspection_cases/<zone>/<os>/<case_name>/script.py` 전체 plain text

## inspection_code 찾기 규칙

- `inspection_code`는 `inspection.md`의 번호를 그대로 쓰는 것이 아니라, 먼저 `inspection_name`에 대응하는 항목을 찾아야 한다.
- 즉 `raw_data.md`의 `세부 점검항목`과 가장 잘 맞는 `inspection.md` 항목을 찾고, 그 번호를 `SVR-x-y` 형식으로 바꾼다.

예시:

- `inspection.md`
  - `## ⑥ 클러스터`
  - `### ⑥-1 Cluster 데몬 상태`
- 대응 케이스
  - `solaris_cluster_daemon_scstat_check`
- 결과
  - `inspection_code = SVR-6-1`

## 작성 절차

1. 대상 OS를 정한다.
2. `example.md`에서 키 구조와 순서를 확인한다.
3. `inspection_cases/` 아래 zone을 순회해 대상 케이스 디렉터리를 찾는다.
4. 각 케이스의 `raw_data.md`와 `script.py`를 읽는다.
5. `raw_data.md`의 `세부 점검항목`을 기준으로 `inspection.md`에서 일치 항목을 찾는다.
6. 일치 항목 번호로 `inspection_code`를 만든다.
7. `example.md`의 키 순서대로 결과 md를 작성한다.
8. 결과 파일명이 `case_name`과 동일한지 확인한다.

사용자가 `api_data/os/<os>/*.md를 모두 작성해줘`라고 하면 위 절차를 전체 케이스에 반복 적용한다.

## 검증 체크리스트

- 키 이름이 `example.md`와 완전히 같은가
- 키 순서가 `example.md`와 같은가
- `inspection_name`, `inspection_content`, `inspection_command`, `inspection_output`, `description`, `thresholds`가 `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`와 일치하는가
- `category_name`이 `raw_data.md`의 `영역`과 일치하는가
- `inspection_code`가 `inspection.md`의 일치 항목 번호를 `SVR-x-y` 형식으로 변환한 값과 일치하는가
- `inspection_script`가 `script.py` 전체 plain text와 일치하는가
- 결과 파일명이 `case_name`과 같은가
- zone을 고정값으로 가정하지 않았는가

## 금지 사항

- `example.md`에 없는 키를 임의로 추가하지 않는다.
- `inspection_name`과 `inspection_content`를 같은 값으로 복사하지 않는다.
- 예전 경로 `raw_data/<os>/<case_name>.md`를 기준으로 삼지 않는다.
- `thresholds`를 예전 `case.json` 기준으로 되돌리지 않는다.
- `inspection_script`를 요약하거나 fenced code block으로 감싸지 않는다.
- zone을 `server`로 고정해서 찾지 않는다.
- 이 문서를 근거로 API 호출이나 서버 등록을 하지 않는다.

## Solaris 예시

- 결과 파일: `api_data/os/solaris/solaris_memory_recognition_prtdiag_check.md`
- `category_name`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/raw_data.md`의 `영역`
- `inspection_name`: `raw_data.md`의 `세부 점검항목`
- `inspection_content`: `raw_data.md`의 `점검 내용`
- `inspection_command`: `raw_data.md`의 `명령어`
- `inspection_output`: `raw_data.md`의 `출력 결과`
- `description`: `raw_data.md`의 `설명`과 `판단기준`
- `thresholds`: `raw_data.md`의 `임계치`
- `inspection_script`: `script.py`
- `inspection_code`: `inspection.md`에서 일치하는 항목 번호 `②-2`를 찾아 `SVR-2-2`로 변환
