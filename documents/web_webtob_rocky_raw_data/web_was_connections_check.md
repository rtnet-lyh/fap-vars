# 영역
환경설정

# 세부 점검항목
WEB-WAS 연동상태 점검

# 점검 내용
WEB-WAS 커넥션 상태가 지속적으로 연결되어 있어야 웹서버로 요청 시 WAS 응답 후 정상적인 서비스가 이뤄졌는지 점검(만료 시 Https 서비스 시 보안 취약 발생)

# 구분
권고

# 명령어
```bash
webtob_ctl status
```

# 출력 결과
```text
Status: RUNNING
MaxConnections: 1000
MaxRequestPerConnection: 50
MaxWorkerThreads: 200
```

# 설명
- Status: RUNNING 상태는 WebtoB와 WAS 간의 커넥션이 정상적으로 유지되고 있음을 나타냄. 상태가 RUNNING이 아닌 STOPPED나 ERROR 상태 라면, 시스템 로그 확인 점검 필요


# 임계치
connection_status: WebtoB와 WAS 간의 커넥션 상태

# 판단기준
- **양호**: `connection_status`가 RUNNING인 상태
- **경고**: `connection_status`가 RUNNING이 아닌 STOPPED나 ERROR인 상태
- **확인 필요**: webtob_ctl 명령이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
