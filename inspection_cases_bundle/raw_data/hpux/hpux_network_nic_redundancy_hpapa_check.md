# 영역
NETWORK

# 세부 점검항목
NIC 이중화 점검

# 점검 내용
HP-UX APA 또는 네트워크 이중화 구성의 정상 동작 여부를 점검한다.

# 구분
권고

# 명령어
```bash
netstat -in
lanscan -q
```

# 출력 결과
```text
Name  Mtu   Network         Address            Ipkts Ierrs Opkts Oerrs Coll
lan0  1500  192.168.1.0     192.168.1.136      12000     0 11000     0    0
lan1  1500  192.168.1.0     192.168.1.137      11800     0 10900     0    0

State of LAN Interface(s)
NamePPA  Hardware Path        Station Address    HP-DLPI   Link
lan0PPA  0/1/2/0/0/0           0x001560A1B2C3     UP        UP
lan1PPA  0/1/2/0/0/1           0x001560A1B2C4     UP        UP
```

# 설명
- `netstat -in`과 `lanscan -q`로 운영 NIC와 링크 상태, 오류 카운터를 확인한다.
- HP Auto Port Aggregation(APA) 구성 환경에서는 APA 관리 명령 또는 구성 파일로 active/standby 및 aggregation 상태를 추가 확인한다.
- 이중화 대상 NIC 중 하나라도 DOWN이면 단일 장애점 또는 failover 상태일 수 있다.
- 오류 카운터가 증가하거나 한쪽 링크만 동작하면 케이블, 스위치, APA 설정을 점검한다.

# 임계치
required_redundant_nic_count
max_interface_error_count

# 판단기준
- **양호**: 이중화 대상 NIC가 모두 UP이고 오류 카운터 증가가 없는 경우
- **경고**: 이중화 대상 NIC DOWN, 오류 증가, active/standby 구성 불일치가 있는 경우
- **확인 필요**: APA 구성 여부 또는 기대 이중화 대상 NIC 목록이 불명확한 경우
