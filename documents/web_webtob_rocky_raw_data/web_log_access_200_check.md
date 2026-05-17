# 영역
로그

# 세부 점검항목
접근 로그 점검

# 점검 내용
사용자(클라이언트) 요청이 웹서버에 정상적으로 접속되어 서비스 되는지 WEB Access log 확인

# 구분
필수

# 명령어 - access_log_path: /home/exTMS/tmax/webtob/log/main
```bash
awk '$(NF-2)=200' $(ls {{ access_log_path }}/access.log*|sort|tail -n 1) | tail -20
```

# 출력 결과
```text
[root@tips_web1 main]# awk '$(NF-2)=200' $(ls /home/exTMS/tmax/webtob/log/main/access.log*|sort|tail -n 1) | tail -20
172.18.12.53 [08/May/2026:17:57:42 +0900] "POST /getNotiPopupInfo.do HTTP/1.1" 200 12 5
172.29.53.51 [08/May/2026:17:57:42 +0900] "GET /trafficMonitor/trafficData?source=trafficVdsCorrectionLine&sourceLayer=VDS_TRAFFIC_CORRECTION&_=1778222531851 HTTP/1.1" 200 10553961 156
172.18.12.53 [08/May/2026:17:57:42 +0900] "POST /getOpinionPopupInfo.do HTTP/1.1" 200 12 2
172.18.12.53 [08/May/2026:17:57:42 +0900] "POST /checkSession.do HTTP/1.1" 200 14 0
```

# 설명
- 접근 로그 점검: grep "200" 명령어를 사용하여 HTTP 상태 코드 200을 포함한 로그를 검색함. HTTP 상태 코드 200이 많이 발견되면 서비스가 정상적으로 운영되고 있으며, 상태 코드 200이 발견되지 않을 경우 서비스의 정상 작동 여부를 점검하고 문제를 해결을 권고. 

# 임계치

# 판단기준
- **양호**: HTTP 상태 코드 200이 발견되는 상태
- **경고**: HTTP 상태 코드 200이 발견되지 않는 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
