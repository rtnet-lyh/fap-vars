# FAP -> VARS 계정정보 동기화 도구

`sync_credentials.py`는 `fap` DB의 호스트 계정정보를 읽어서 `vars` DB의 애플리케이션 계정정보로 동기화한다.

기본 동작은 dry-run이다. `--apply`를 줘야 실제 UPDATE를 수행한다.

## 파일 구성

- `sync_credentials.py`: 동기화 CLI
- `sample_config.yml`: 샘플 설정
- `requirements.txt`: 실행 의존성
- `test_sync_credentials.py`: 단위 테스트

## 설치

```bash
python3 -m pip install -r credential_sync/requirements.txt
```

## 실행

dry-run:

```bash
python3 credential_sync/sync_credentials.py --config credential_sync/sample_config.yml
```

실제 반영:

```bash
python3 credential_sync/sync_credentials.py --config credential_sync/sample_config.yml --apply
```

실행이 끝나면 아래 정보가 출력된다.

- 실행 모드
- report JSON 경로
- 중단 여부
- 평가한 `host_application_info` 행 수
- 업데이트 가능 건수
- 실제 반영 건수
- 판정별 건수

## 동기화 기준

- `fap.host_info.is_enable = 1` 인 호스트만 사용한다.
- `vars.host_info.is_enable = 1` 인 호스트만 사용한다.
- `host_info.host_ip` exact match 로만 매칭한다.
- `vars.host_application_info` 가 있는 대상만 평가한다.
- `vars.credential_host_application_info` 가 이미 있는 대상만 업데이트한다.
- `credential_type_id = 3` 은 기본 제외한다.
- 기본 설정에서는 source/target `credential_type_id` 가 같을 때만 업데이트한다.
- `input_data` 는 키 병합이 아니라 source 문자열 전체로 교체한다.
- 복호화/재암호화는 이번 버전에 포함하지 않는다.

## YAML 설정

`source_db`, `target_db`, `sync` 3개 블록을 사용한다.

### DB 설정

- `host`
- `port`
- `dbname`
- `user`
- `password`

`dbname` 대신 `database` 키도 허용한다.

### sync 설정

- `exclude_credential_type_ids`: 제외할 credential type ID 배열. 기본값은 `[3]`
- `require_same_credential_type`: `true` 이면 source/target 타입이 같을 때만 업데이트
- `allowed_area_names`: 허용 분야명 배열. 예: `["서버", "DBMS"]`
- `modified_by`: 실제 UPDATE 시 `modified_by`로 기록할 사용자 ID. 비우면 기존 값 유지
- `report_path`: 결과 JSON 파일 경로

### allowed_area_names

`allowed_area_names` 는 배열 형태로 입력한다.

```yaml
sync:
  allowed_area_names:
    - "서버"
    - "DBMS"
```

- 값이 없거나 빈 배열이면 분야 필터를 적용하지 않는다.
- 비교 대상은 `vars.host_application_info.area_id -> vars_area.name` 이다.
- 비교 방식은 trim 후 exact match 다.

## 결과 JSON

report JSON에는 아래 정보가 들어간다.

- `host_ip_summary`: 활성 호스트 수, 교집합 IP 수, 교집합 상세
- `decision_counts`: 판정별 건수
- `eligible_updates`: 업데이트 가능 건수
- `applied_updates`: 실제 반영 건수
- `duplicate_ip_errors`: 양쪽 활성 host master 에 중복 IP 가 있으면 중단 사유 기록
- `updates`: 업데이트 가능 행 상세
- `skipped`: 제외된 행 상세

보안상 `input_data` 원문은 report JSON에 저장하지 않는다.
