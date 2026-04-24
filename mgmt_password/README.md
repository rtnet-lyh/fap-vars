# 호스트 엑셀 비밀번호 일괄 갱신 도구

`update_host_passwords.py`는 호스트 엑셀 파일을 읽어서 조건에 맞는 행의 `password`, `become_password`를 일괄 갱신한 뒤 새 엑셀 파일로 저장한다. 저장된 결과 파일에는 두 번째 시트 `업데이트 결과`가 추가되며, 각 행에 `업데이트됨` 컬럼으로 `됨` 또는 `안됨`이 표시된다.

## 파일 구성

- `update_host_passwords.py`: 비밀번호 갱신 스크립트
- `sample_rules.json`: 샘플 설정 파일
- `호스트_파일_다운로드2026-04-21.xlsx`: 입력 예시 파일

## 사전 준비

`openpyxl`이 필요하다.

```bash
python3 -m pip install -r ../report/requirements.txt
```

## 실행 방법

현재 디렉터리에서 아래처럼 실행한다.

```bash
python3 update_host_passwords.py --config sample_rules.json
```

다른 설정 파일을 쓰려면 `--config`에 JSON 경로를 넣으면 된다.

```bash
python3 update_host_passwords.py --config my_rules.json
```

실행이 끝나면 아래 정보를 출력한다.

- 생성된 출력 파일 경로
- 읽은 데이터 행 수
- `password` 변경 건수
- `become_password` 변경 건수
- 행 단위 `업데이트됨` 건수
- 행 단위 `안됨` 건수
- 규칙별 적용 건수

## JSON 형식

최상위 필드는 아래 4개를 사용한다.

- `input_excel`: 원본 엑셀 경로
- `output_excel`: 새로 생성할 엑셀 경로
- `password_rules`: `password` 갱신 규칙 배열
- `become_password_rules`: `become_password` 갱신 규칙 배열

경로가 상대경로면 JSON 파일이 있는 디렉터리 기준으로 해석한다.

`match` 안의 `분야`, `OS/애플리케이션`, `계정형식`, `사용자명`은 문자열 1개 또는 문자열 배열로 입력할 수 있다.

- 문자열: 해당 값과 정확히 일치
- 배열: 배열 안 값 중 하나와 일치하면 매칭

```json
{
  "input_excel": "호스트_파일_다운로드2026-04-21.xlsx",
  "output_excel": "호스트_파일_다운로드2026-04-21_updated.xlsx",
  "password_rules": [
    {
      "match": {
        "분야": ["서버"],
        "OS/애플리케이션": ["LINUX", "UNIX"],
        "계정형식": ["SSH"],
        "사용자명": ["sdfsdf"]
      },
      "pattern": {
        "type": "manager_name",
        "prefix": "pw_",
        "start": 1,
        "end": 5,
        "suffix": "!"
      }
    }
  ],
  "become_password_rules": [
    {
      "match": {
        "분야": ["서버"],
        "OS/애플리케이션": ["UNIX"],
        "계정형식": ["SSH"],
        "사용자명": ["sdfsdf"]
      },
      "pattern": {
        "type": "ip_octet_4_padded",
        "prefix": "root_",
        "start": 2,
        "end": 3,
        "suffix": "#"
      }
    }
  ]
}
```

## 규칙 작성 방법

각 규칙은 `match`와 `pattern`을 가진다.

### 1. `match`

허용하는 키는 아래 4개뿐이다.

- `분야`
- `OS/애플리케이션`
- `계정형식`
- `사용자명`

`사용자명`은 계정 컬럼으로 보면 된다.

`match` 값은 문자열 1개 또는 문자열 배열로 넣을 수 있다.

- 문자열: 해당 값과 정확히 일치해야 한다.
- 배열: 배열 안 값 중 하나와 일치하면 된다.

`match`에 적은 키만 검사한다. 적지 않은 키는 검사하지 않는다.

예를 들어 아래 규칙은 `분야`가 `서버` 또는 `네트워크`이고, `계정형식`이 `SSH`인 행에 적용된다. `OS/애플리케이션`, `사용자명`은 검사하지 않는다.

```json
{
  "match": {
    "분야": ["서버", "네트워크"],
    "계정형식": "SSH"
  }
}
```

배열은 비어 있으면 안 된다.

여러 규칙이 같은 행에 동시에 맞으면 먼저 작성한 규칙 1개만 적용된다.

### 배열 입력 예시

아래처럼 문자열과 배열을 섞어서 사용할 수 있다.

```json
{
  "match": {
    "분야": ["서버", "네트워크"],
    "OS/애플리케이션": ["LINUX", "UNIX", "WINDOWS"],
    "계정형식": ["SSH", "WINRM"],
    "사용자명": ["root", "administrator", "ansible"]
  }
}
```

이 규칙은 아래 의미다.

- `분야`가 `서버` 또는 `네트워크`
- `OS/애플리케이션`이 `LINUX`, `UNIX`, `WINDOWS` 중 하나
- `계정형식`이 `SSH` 또는 `WINRM`
- `사용자명`이 `root`, `administrator`, `ansible` 중 하나

즉 각 키 내부는 OR 조건으로 동작한다.

### 2. `pattern`

`pattern` 필드는 아래를 사용한다.

- `type`: 패턴 타입
- `prefix`: 필수값
- `suffix`: 선택값, 없으면 빈 문자열
- `start`: 선택값
- `end`: 선택값

모든 `type`에서 `start`, `end`를 사용할 수 있다.

- `start`, `end`가 없으면 전체 문자열 사용
- `start`, `end`가 있으면 1부터 시작하는 inclusive 방식으로 부분 문자열 사용

예를 들어 `관리명=testhost1`, `start=2`, `end=5`면 `esth`를 사용한다.
예를 들어 `ip_octet_4_padded`에서 `123`, `start=2`, `end=3`이면 `23`을 사용한다.

타입별 허용 범위는 아래와 같다.

- `manager_name`: `1`부터 `50`
- `ip_all`, `ip_all_padded`: `1`부터 `12`
- `ip_octet_*`, `ip_octet_*_padded`: `1`부터 `3`

## 패턴 타입

### 관리명 기반

| type | 설명 | 예시 결과 |
| --- | --- | --- |
| `manager_name` | `관리명` 전체 또는 일부 사용 | `host01` |

### IP 기반

IP 기반 패턴은 항상 `.`을 제거한 값을 기준으로 계산한다.

예시 IP: `192.168.1.123`

| type | 설명 | 예시 결과 |
| --- | --- | --- |
| `ip_all` | 점 제거 후 전체 또는 일부 사용 | `1921681123` |
| `ip_all_padded` | 각 옥텟을 3자리 zero-pad 후 점 없이 연결 | `192168001123` |
| `ip_octet_1` | 첫 번째 옥텟 | `192` |
| `ip_octet_2` | 두 번째 옥텟 | `168` |
| `ip_octet_3` | 세 번째 옥텟 | `1` |
| `ip_octet_4` | 네 번째 옥텟 | `123` |
| `ip_octet_1_padded` | 첫 번째 옥텟 3자리 | `192` |
| `ip_octet_2_padded` | 두 번째 옥텟 3자리 | `168` |
| `ip_octet_3_padded` | 세 번째 옥텟 3자리 | `001` |
| `ip_octet_4_padded` | 네 번째 옥텟 3자리 | `123` |

옥텟 타입도 `start`, `end`를 지원한다.

- 예: `ip_octet_2`, 값 `168`, `start=2`, `end=3` -> `68`
- 예: `ip_octet_3_padded`, 값 `001`, `start=1`, `end=2` -> `00`

## 최종 비밀번호 생성 방식

최종 값은 항상 아래 형식으로 만들어진다.

```text
prefix + 본문 + suffix
```

예시:

- `prefix=test`
- `type=manager_name`
- `관리명=testhost1`
- `start=1`
- `end=4`
- `suffix=!`

결과:

```text
testtest!
```

## `become_password_rules` 동작

`become_password_rules`는 아래 조건을 모두 만족할 때만 적용된다.

- `match` 조건이 맞을 것
- 행의 `become` 값이 true로 해석될 것

아래 값들은 true로 해석한다.

- Excel boolean `True`
- 문자열 `1`, `true`, `t`, `yes`, `y`, `on`

## 입력 엑셀 조건

첫 번째 시트만 처리한다.

필수 헤더는 아래와 같다.

- `IP`
- `관리명`
- `분야`
- `OS/애플리케이션`
- `계정형식`
- `사용자명`
- `password`
- `become`
- `become_password`

원본 파일의 헤더, 열 순서, 스타일, freeze pane은 유지한다.

출력 파일에는 두 번째 시트 `업데이트 결과`가 추가된다.

- 첫 번째 시트: 실제 비밀번호가 반영된 결과
- 두 번째 시트: 모든 데이터 행 + `업데이트됨` 컬럼
- `업데이트됨=됨`: 해당 행에서 `password` 또는 `become_password` 중 하나 이상 변경됨
- `업데이트됨=안됨`: 해당 행에서 실제 변경된 값이 없음

## 주의사항

- 원본 엑셀은 수정하지 않고 새 파일만 생성한다.
- `output_excel`이 원본과 같으면 실패한다.
- `output_excel` 파일이 이미 존재해도 실패한다.
- IP는 IPv4 4옥텟 형식만 허용한다.
- `start`, `end`는 1 이상이어야 한다.
- `start > end`이면 실패한다.
- `manager_name`에서 `start`, `end`는 50을 넘을 수 없다.
- `ip_all`, `ip_all_padded`에서 `start`, `end`는 12를 넘을 수 없다.
- `ip_octet_*`, `ip_octet_*_padded`에서 `start`, `end`는 3을 넘을 수 없다.
- `end`가 문자열 길이를 넘으면 실패한다.

## 빠른 시작

1. `sample_rules.json`을 복사해서 새 JSON 파일을 만든다.
2. `input_excel`, `output_excel`, 규칙을 수정한다.
3. `python3 update_host_passwords.py --config <설정파일>`로 실행한다.
4. 생성된 새 엑셀 파일을 확인한다.
