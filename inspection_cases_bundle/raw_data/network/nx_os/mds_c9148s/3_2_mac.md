# 영역
서비스

# 세부 점검항목
MAC/Arp Table 상태 확인

# 점검 내용
MAC/Arp Table 정상 여부 확인

# 구분
권고

# 명령어
```bash
show arp
```

# 출력 결과
```text
CITS-SAN1# show arp
Protocol Address         Age (min) Hardware Addr                 Type Interface
Internet 193.1.0.254     0         0000.0c07.acc1                ARPA mgmt0

```

# 설명
- 명령어: arp 테이블(IP와 MAC 주소간의 매핑정보 저장 테이블) 정보를 확인하는 명령어.

[참고]
- IP와 MAC 이 정상적으로 매핑이 되는지 확인하는 항목. 어떤 값이 정상 값인지 판단 힘듦
1안. Hardware Addr과 Interface가 정상적으로 출력 되면 양호처리.
2안. 정상인 IP와 MAC 값을 변수로 받아 일치하면 양호처리.
3안. 출력만 하고 담당자 확인처리.

# 임계치


# 판단기준
- **양호**: 참고를 참고하세요 .. 
- **경고**: 
- **확인 필요**: 