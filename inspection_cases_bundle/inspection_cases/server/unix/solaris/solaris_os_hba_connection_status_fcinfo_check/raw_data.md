# 영역
OS

# 세부 점검항목
HBA 연결 정상 유무 점검

# 점검 내용
Solaris 서버의 HBA 포트 연결 상태와 현재 링크 속도를 점검합니다.

# 구분
필수

# 명령어
```bash
fcinfo hba-port
```

# 출력 결과
```text
# fcinfo hba-port
HBA Port WWN: 10000000c9612345
OS Device Name: /dev/cfg/c2
Manufacturer: Emulex
Model: LPe12062
Firmware Version: 2.02a16
FCode/BIOS Version: 3.33a4
Serial Number: MY12345
Driver Name: lpfc
Driver Version: 9.2.0
State: online
Supported Speeds: 2Gb 4Gb 8Gb
Current Speed: 8Gb
Node WWN: 20000000c9612345
```

# 설명
- `fcinfo hba-port`는 HBA 포트별 WWN, 장치명, 드라이버, State, 링크 속도를 확인할 때 사용합니다.
- 각 포트의 `State`가 `online`이고 `Current Speed`가 기준 속도 이상이면 정상으로 판단합니다.
- `offline` 상태이거나 속도가 기준 미만이면 포트 연결 상태, 광케이블, 스위치 및 설정을 점검해야 합니다.
- `fcinfo` 명령이 없거나 출력 형식을 해석할 수 없으면 실패로 처리합니다.

# 임계치
- `expected_state_value`: `online`
- `min_current_speed_gbps`: `8`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 모든 HBA 포트가 `State=online`이고 `Current Speed`가 `8Gb` 이상인 경우
- **실패**: 포트가 `offline`이거나 `Current Speed`가 기준 미만인 경우
- **실패**: `fcinfo` 명령 실행 실패, 명령 미설치, 출력 파싱 실패, 오류 로그 확인 시
