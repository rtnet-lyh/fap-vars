# API Data Markdown 작성 규칙

이 문서는 `inspection_cases_bundle/api_data/os/<os>/*.md` 파일을 생성하거나 수정할 때 사용하는 공통 작업 지침이다.

이 문서만 읽어도 다음 세션에서 동일한 방식으로 `api_data/os/<os>/*.md`를 만들 수 있어야 한다.

## 이 문서로 해야 하는 일

사용자가 아래처럼 요청하면 이 문서를 기준으로 **md 생성 작업만** 수행한다.

```text
/api_data/introduction.md를 기준으로 해서 api_data/os/<os>/*.md를 작성해줘
```

이 요청을 받았을 때 해야 하는 일은 다음뿐이다.

- `api_data/os/<os>/*.md`를 새로 만든다.
- 이미 있으면 규칙에 맞게 수정한다.
- `example.md`, `inspection.md`, `raw_data`, `case.json`, `script.py`를 참조해 값을 채운다.

이 요청을 받았을 때 하면 안 되는 일은 다음이다.

- `inspection_lookup.py`를 실행하지 않는다.
- `inspection_create.py`를 실행하지 않는다.
- 세션을 사용한 API 호출을 하지 않는다.
- 서버 등록을 시도하지 않는다.

즉, 이 문서는 **API 등록 문서가 아니라 md 생성 문서**이다.

API 조회 또는 서버 등록은 `api_data/inspection_register/REGISTER_WORKFLOW.md`의 범위이며, 이 문서의 범위가 아니다.

## 목적

- 목적은 `api_data/os/<os>/*.md` 문서를 생성하는 것이다.
- 결과 문서는 `api_data/os/<os>/참고/example.md`와 동일한 키 구조를 가져야 한다.
- 각 키의 값은 아래 자료를 조합해서 채운다.
  - `api_data/os/<os>/참고/inspection.md`
  - 매칭되는 `inspection_cases/<zone>/<os>/<case_name>/script.py`
  - 매칭되는 `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`

이 문서의 목적에는 API 호출, id 조회, 서버 등록이 포함되지 않는다.


## 기본 원칙

- 결과 파일의 키 이름은 반드시 `api_data/os/<os>/참고/example.md`와 동일해야 한다.
- 키 순서도 반드시 `api_data/os/<os>/참고/example.md`와 동일해야 한다.
- 값은 임의로 꾸미지 말고 지정된 출처에서 가져온다.
- 동일한 정보를 여러 출처에서 얻을 수 있으면 우선순위 규칙을 따른다.

## 입력 자료

문서 1건을 만들 때 사용하는 입력 자료는 아래와 같다.

1. `api_data/os/<os>/참고/example.md`
2. `api_data/os/<os>/참고/inspection.md`
3. `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`
4. `inspection_cases/<zone>/<os>/<case_name>/script.py`

  ### 정보 목록:
  
  type_name  :  api_data/os/<os>/참고/example.md와 동

  area_name   : api_data/os/<os>/참고/example.md와 동

  category_name : inspection_cases/<zone>/<os>/<case_name>/raw_data.md의 영역과 동

  application_type  : api_data/os/<os>/참고/example.md와 동

  application: api_data/os/<os>/참고/example.md와 동

  inspection_code:  api_data/os/<os>/참고/inspection.md 중 inspection_name과 일치하는 번호를 기반으로 생성한 값

  is_required: inspection_cases/<zone>/<os>/<case_name>/raw_data.md의 필수 여부와 동 (없을 시 default 필수)

  inspection_name : inspection_cases/<zone>/<os>/<case_name>/raw_data.md의 세부 점검항목과 동 

  inspection_content: inspection_cases/<zone>/<os>/<case_name>/raw_data.md의 점검항목과 동

  inspection_command: inspection_cases/<zone>/<os>/<case_name>/raw_data.md의 명령어와 동

  inspection_output: inspection_cases/<zone>/<os>/<case_name>/raw_data.md의 출력 결과와 동

  description: inspection_cases/<zone>/<os>/<case_name>/raw_data.md의 설명과 판단기준을 합친 것과 동

  thresholds: inspection_cases/<zone>/<os>/<case_name>/raw_data.md의 임계치와 동

  inspection_script: inspection_cases/<zone>/<os>/<case_name>/script.py와

  ### 주의점:

  만들고자 하는 이름은: <application>_<category_name>_<inspection_name(english)>_<command>.md
  즉, 이름이 이미 생성되어있는 inspection_cases/<zone>/<os>/<case_name>의 <case_name>과 동일하다.
  이때 나머지는 모두 동일한 case_name의 파일로부터 값을 가져오면 되지만,
  inspection_code의 경우에는 case_name과 category_name을 풀이해서, api_data/os/<os>/참고/inspection.md의 내용 중 일치하는 번호를 가져와야한다. 
  ex: 

  inspection_md에서 

  ## ⑥ 클러스터

  ### ⑥-1 Cluster 데몬 상태
  - **점검 항목**: Cluster 정상 유무 점검
  - **명령어**:

  일 경우

  category_name은 cluster

  inspection_name(english)은 cluster daemon status 이다.

  /home/fap/projects/fap-vars/inspection_cases_bundle/inspection_cases/server/solaris 중 

  solaris_cluster_* 중에 가장 적합한건 solaris_cluster_daemon_scstat_check로 찾아지게 된다. 

  그러므로, solaris_cluster_daemon_scstat_check의 inspection_code의 정보는 ⑥-1이 되며, 하단의 규칙에 따르면 
  
  SVR-6-1이 된다. 


## zone 탐색 규칙

- `inspection_cases/<zone>/<os>/...`에서 `<zone>`은 고정값이 아니다.
- 현재는 `server`가 대표적이지만, 이후 다른 zone이 생길 수 있다.
- 따라서 OS별 케이스를 찾을 때는 zone 이름을 가정하지 말고 `inspection_cases/` 아래 zone 폴더들을 순회해야 한다.
- 그리고 각 zone 아래에서 원하는 `<os>` 폴더가 있는지 확인해 매칭되는 케이스를 찾는다.

예시:

- `inspection_cases/server/solaris/...`
- `inspection_cases/network/solaris/...`
- `inspection_cases/db/solaris/...`

## 결과 파일명 규칙

- 결과 md 파일명은 대응하는 케이스명과 동일해야 한다.
- 예: 케이스 디렉터리가 `inspection_cases/server/solaris/solaris_disk_filesystem_usage_df_check/`라면 결과 파일명은 `api_data/os/solaris/solaris_disk_filesystem_usage_df_check.md`이다.
- 파일명은 소문자 snake case를 유지한다.

## 값 매핑 규칙

### 1. 템플릿 키

- 키 이름은 `api_data/os/<os>/참고/example.md`를 그대로 사용한다.
- 키 순서도 `example.md`와 동일해야 한다.

### 2. type_name, area_name, application_type, application, is_required

- `type_name`, `area_name`, `application_type`, `application`은 `api_data/os/<os>/참고/example.md`와 동일하다.
- `is_required`는 `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 필수 여부를 사용하고, 없으면 기본값 `필수`를 사용한다.

### 3. category_name

- `category_name`은 `example.md`의 값을 고정 사용하지 않는다.
- `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `영역` 값을 가져와 사용한다.

### 4. inspection_code

- `inspection_code`는 `api_data/os/<os>/참고/inspection.md`에서 `inspection_name`과 일치하는 항목 번호를 찾은 뒤 생성한다.
- 예: 일치하는 항목 번호가 `②-2`이면 `SVR-2-2`

### 5. inspection_name

- `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `세부 점검항목` 값을 사용한다.

### 6. inspection_content

- `inspection_content`는 `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `점검 내용` 값을 사용한다.
- 따라서 `inspection_name`과 `inspection_content`는 서로 다른 값일 수 있다.

### 7. inspection_command

- `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `명령어`를 사용한다.

### 8. inspection_output

- `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `출력 결과`를 사용한다.

### 9. description

- `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `설명`과 `판단기준`을 합쳐 사용한다.

### 10. thresholds

- `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `임계치`를 사용한다.
- 결과 표현 형식은 `example.md`에 맞춘다.

### 11. inspection_script

- 대응하는 `inspection_cases/<zone>/<os>/<case_name>/script.py` 전체 본문을 그대로 넣는다.
- 축약하지 않는다.
- fenced code block으로 감싸지 않는다.
- plain text로 둔다.

## 작성 절차

1. 대상 OS를 정한다.
2. `api_data/os/<os>/참고/example.md`에서 키 구조와 출력 형식을 확인한다.
3. `inspection_cases/` 아래 zone 폴더를 순회하면서 같은 OS 폴더 안의 대응 케이스 디렉터리를 찾는다.
4. 찾은 케이스의 `raw_data.md`, `script.py`를 읽는다.
5. `raw_data.md`의 `세부 점검항목`을 기준으로 `api_data/os/<os>/참고/inspection.md`에서 일치하는 항목을 찾는다.
6. 찾은 항목 번호를 `SVR-x-y` 형식의 `inspection_code`로 변환한다.
7. `example.md`의 키 이름과 순서를 그대로 유지해 `api_data/os/<os>/<case_name>.md`를 작성한다.
8. 값은 `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`와 `script.py` 기준으로 채운다.
9. 결과 파일명이 케이스명과 일치하는지 확인한다.

사용자가 `api_data/os/<os>/*.md를 모두 작성해주세요`라고 하면 위 절차를 전체 케이스에 반복 적용해 일괄 생성한다.

## 필수 규칙

- `example.md`에 있는 키는 하나도 빠지면 안 된다.
- 키 순서는 `example.md`와 같아야 한다.
- `inspection_code`는 `inspection_name`과 일치하는 `inspection.md` 항목 번호와 연결되어야 한다.
- `inspection_name`, `inspection_content`, `inspection_command`, `inspection_output`, `description`, `thresholds`는 `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`와 일치해야 한다.
- `inspection_script`는 반드시 `script.py` 전체와 일치해야 한다.
- `inspection_script`는 plain text여야 한다.
- zone은 고정하지 말고 순회해서 찾는다.

## 케이스 찾기 규칙

- 먼저 케이스명 규칙 `<application>_<category_name>_<inspection_name(english)>_<command>`를 기준으로 대응 케이스를 식별한다.
- 실제 결과 파일명은 이미 생성되어 있는 `inspection_cases/<zone>/<os>/<case_name>/`의 `case_name`과 동일해야 한다.
- 케이스를 찾은 뒤 `raw_data.md`의 `세부 점검항목`을 기준으로 `inspection.md`에서 일치하는 항목 번호를 찾는다.
- 케이스명은 기존 `inspection_cases/.../<case_name>/` 디렉터리명과 동일하다.
- 찾은 케이스명으로 `api_data/os/<os>/<case_name>.md`를 만든다.

예시:

- `inspection.md`에서 `## ⑥ 클러스터`, `### ⑥-1 Cluster 데몬 상태`가 있다.
- `category_name`은 `cluster`, `inspection_name(english)`은 `cluster daemon status`로 풀이된다.
- `inspection_cases/server/solaris`에서 가장 적합한 케이스는 `solaris_cluster_daemon_scstat_check`이다.
- 따라서 결과 파일은 `api_data/os/solaris/solaris_cluster_daemon_scstat_check.md`가 되고, `inspection_code`는 `SVR-6-1`이다.

## 검증 체크리스트

- 키 이름이 `api_data/os/<os>/참고/example.md`와 완전히 같은가
- 키 순서가 `example.md`와 같은가
- `inspection_name`, `inspection_content`, `inspection_command`, `inspection_output`, `description`, `thresholds`가 `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`와 일치하는가
- `category_name`이 대응하는 `inspection_cases/<zone>/<os>/<case_name>/raw_data.md`의 `영역`과 맞는가
- `inspection_code`가 `inspection.md`에서 `inspection_name`과 일치하는 번호를 `SVR-x-y` 형식으로 변환한 값과 일치하는가
- `inspection_script`가 `script.py` 전체 plain text와 일치하는가
- 결과 파일명이 케이스명과 같은가
- zone을 고정값으로 가정하지 않았는가

## Solaris 기준 예시

Solaris `②-2 메모리 상태 확인`에 대해 결과 파일을 만들면 아래처럼 매핑한다.

- 결과 파일: `api_data/os/solaris/solaris_memory_recognition_prtdiag_check.md`
- 템플릿 키: `api_data/os/solaris/참고/example.md`
- `category_name`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/raw_data.md`의 `영역`
- `inspection_code`: `inspection.md`에서 `inspection_name`과 일치하는 항목 번호 `②-2`를 `SVR-2-2`로 변환
- `inspection_name`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/raw_data.md`의 `세부 점검항목`
- `inspection_content`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/raw_data.md`의 `점검 내용`
- `inspection_command`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/raw_data.md`의 `명령어`
- `inspection_output`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/raw_data.md`의 `출력 결과`
- `description`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/raw_data.md`의 `설명`과 `판단기준`
- `thresholds`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/raw_data.md`의 `임계치`
- `inspection_script`: `inspection_cases/<zone>/solaris/solaris_memory_recognition_prtdiag_check/script.py` 전체 plain text

## 금지 사항

- `example.md`에 없는 키를 임의로 추가하지 않는다.
- `inspection.md`에 있는 점검 항목을 임의로 다른 번호와 섞지 않는다.
- `inspection_content`를 `inspection_name`과 같은 값으로 복사하지 않는다.
- `inspection_cases/<zone>/<os>/<case_name>/raw_data.md` 대신 예전 `raw_data/<os>/<case_name>.md` 경로를 기준으로 작성하지 않는다.
- `thresholds` 값을 예전 `case.json` 기준으로 되돌리지 않는다.
- `inspection_script`를 요약문으로 대체하지 않는다.
- `inspection_script`를 fenced code block으로 감싸지 않는다.
- zone을 `server`로 고정해서 찾지 않는다.
- 이 문서를 근거로 `inspection_lookup.py`를 실행하지 않는다.
- 이 문서를 근거로 `inspection_create.py`를 실행하지 않는다.
- 이 문서를 근거로 `api_data/session.md`를 사용한 API 호출을 하지 않는다.
