# 영역
서비스

# 세부 점검항목
서비스 포트 접속 정상 확인

# 점검 내용
출발지Ip에서 목적지Ip 포트로 통신이 정상적으로 이뤄지는지 점검(방화벽 또는 보안장비 차단 여부 확인)

# 구분
필수

# 명령어

- ip_addr 변수, webtob_service_port 변수
```bash
telnet {{ ip_addr }} {{ webtob_service_port }}
```

# 출력 결과
```text
[root@sd_tipswebwas ~]# telnet 172.18.9.3 9080
Trying 172.18.9.3...
Connected to 172.18.9.3.
Escape character is '^]'.
```

# 설명
- 연결 상태: 연결 성공 여부를 나타내며, 연결이 성공하면 메시지가 표시됨.(Connected to)
[목적지 IP] 메시지가 출력되어야 함. 연결 실패 시 방화벽 또는 보안 장비의 설정 점검 필요.

# 임계치

# 판단기준
- **양호**: "Connected to" 문구가 있는 경우
- **경고**: "Connected refused", "time out", "No route to host", "Unable to connect" 등의 문구가 있는 경우
- **확인 필요**: telnet 명령이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
