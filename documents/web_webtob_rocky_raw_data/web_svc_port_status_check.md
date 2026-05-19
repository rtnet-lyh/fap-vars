# 영역
서비스

# 세부 점검항목
서비스 포트 오픈 상태 점검

# 점검 내용
WEB 프로세스 기동 시 생성되는 사용자 접속 Port가 정상적으로 오픈되었는지 확인을 통해 URL 서비스 포트로 접속 가능한 상태인지 점검

# 구분
필수

# 명령어 - webtob_service_port 변수
```bash
netstat -an | grep "{{ webtob_service_port }}" # webtob_service_port: 9080
```

# 출력 결과
```text
[root@sd_tipswebwas log]# netstat -an | grep 9080
tcp        0      0 0.0.0.0:9080            0.0.0.0:*               LISTEN
```

# 설명
- 프로토콜: tcp 또는 tcp6이어야 하며, 다른 경우에는 포트 설정 검토를 권고. 
- 로컬 주소 및 포트: 서비스에 설정된 포트와 일치하고 LISTEN 상태여야 하며, 포트가 다를 경우 포트 설정 점검. 
- 상태: LISTEN 상태여야 하며, 그렇지 않을 경우 서비스 시작이나 문제 해결 필요.


# 임계치
allow_stats: LISTEN

# 판단기준
- **양호**: 프로토콜이 tcp 또는 tcp6이면서 `allow_stats`가 LISTEN 상태
- **경고**: 프로토콜이 tcp 또는 tcp6이 아니거나 `allow_stats`가 LISTEN이 아닌 상태
- **확인 필요**: 출력이 비어 있거나 명령 실행 불가/권한/미지원 등의 사유로 점검 불가한 상태
