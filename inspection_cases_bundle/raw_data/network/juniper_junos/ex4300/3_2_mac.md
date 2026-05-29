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
falcon@Center_Server_J4300_A> show arp
MAC Address       Address         Name                      Interface               Flags
40:5b:7f:6d:53:60 172.18.8.191    172.18.8.191              irb.808 [ge-0/0/28.0]   none
44:8a:5b:dc:44:02 172.18.8.230    172.18.8.230              irb.808 [xe-0/0/35.0]   none
00:06:c4:90:0d:53 172.18.8.252    172.18.8.252              irb.808 [ge-0/0/28.0]   none
00:00:5e:00:01:fe 172.18.8.254    172.18.8.254              irb.808 [ge-0/0/28.0]   none
Total entries: 4

```

# 설명
- 명령어: arp 테이블(IP와 MAC 주소간의 매핑정보 저장 테이블) 정보를 확인하는 명령어.

[참고]
- CISCO 장비와 동일함
- IP와 MAC 이 정상적으로 매핑이 되는지 확인하는 항목. 어떤 값이 정상 값인지 판단 힘듦
1안. Hardware Addr과 Interface가 정상적으로 출력 되면 양호처리.
2안. 정상인 IP와 MAC 값을 변수로 받아 일치하면 양호처리.
3안. 출력만 하고 담당자 확인처리.

# 임계치


# 판단기준
- **양호**: 참고를 참고하세요 .. 
- **경고**: 
- **확인 필요**: 