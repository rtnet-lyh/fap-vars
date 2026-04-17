# 영역
NETWORK

# 세부 점검항목
NW 링크 상태 점검

# 점검 내용
Network 연결상태 정상 유무 점검(NIC별 STATE Up, Down, Unknown 상태 확인) 

# 구분
필수

# 명령어
```bash
lanscan -q
lanadmin -x 0
```

# 출력 결과
```text
State of LAN Interface(s)
NamePPA  Hardware Path        Station Address    HP-DLPI   Link
lan0PPA  0/1/2/0/0/0           0x001560A1B2C3     UP        UP
lan1PPA  0/1/2/0/0/1           0x001560A1B2C4     UP        DOWN

Interface = lan0
Link status   : Up
Speed         : 1000 Mbps
Duplex        : Full
Autoneg       : On
```

# 설명
- `lanscan -q` 명령으로 NIC별 링크 상태가 UP인지 확인한다.
- `lanadmin -x <ppa>` 명령으로 대상 NIC의 링크 상태, 속도, duplex 설정을 확인한다.
- 링크가 DOWN 또는 UNKNOWN이면 케이블, 스위치 포트, NIC 장애, 이중화 구성을 점검한다.
- 기대 속도가 정의된 경우 실제 속도와 duplex가 운영 기준과 일치해야 한다.

# 임계치
EXPECT_SPEED_MBPS
REQUIRE_FULL_DUPLEX

# 판단기준
- **양호**: 운영 대상 NIC 링크가 UP이고 기대 속도 및 Full Duplex 기준을 만족하는 경우
- **경고**: 링크 DOWN/UNKNOWN, 속도 불일치, Half Duplex 상태가 확인되는 경우
- **확인 필요**: `lanadmin` 권한 문제 또는 PPA 매핑 확인이 불가능한 경우
