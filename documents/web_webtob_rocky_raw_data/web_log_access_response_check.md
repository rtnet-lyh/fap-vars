# 영역
로그

# 세부 점검항목
연동 결과 로그 점검

# 점검 내용
서비스 페이지 수행 시간 점검(WAS 연동 결과 및 호출된 페이지의 수행 시간 확인)

# 구분
필수

# 명령어 - access_log_path: /home/exTMS/tmax/webtob/log, max_response_time: 1000ms(사용자 지정)
```bash
awk '$NF >= {{ max_response_time }}' $(ls /home/exTMS/tmax/webtob/log/main/access.log*|sort|tail -n 1)
```

# 출력 결과
```text
[root@tips_web1 main]# awk '$NF >= 1000' $(ls /home/exTMS/tmax/webtob/log/main/access.log*|sort|tail -n 1) | head -20
172.34.35.55 [08/May/2026:00:00:03 +0900] "GET /trafficMonitor/trafficData?source=trafficVdsCorrectionLine&sourceLayer=VDS_TRAFFIC_CORRECTION&_=1776238340558 HTTP/1.1" 200 10547450 1083
172.19.22.30 [08/May/2026:00:00:04 +0900] "POST /getVmsAutoTargetDrfInfo.do HTTP/1.1" 200 9591935 2696
172.27.35.52 [08/May/2026:00:00:07 +0900] "GET /trafficMonitor/trafficData?source=trafficVdsCorrectionLine&sourceLayer=VDS_TRAFFIC_CORRECTION&_=1778158355767 HTTP/1.1" 200 10547450 3651
172.27.35.52 [08/May/2026:00:00:08 +0900] "GET /trafficMonitor/trafficData?source=trafficVdsCorrectionLine&sourceLayer=VDS_TRAFFIC_CORRECTION&_=1778158371237 HTTP/1.1" 200 10547450 4152
172.19.41.54 [08/May/2026:00:00:10 +0900] "POST /getVmsAutoTargetDrfInfo.do HTTP/1.1" 200 9591935 2529
```

# 설명
- 상태 코드(200, 500): 오류 상태 코드(500) 발생 시, 서버 로그 및 설정을 점검하여 문제 해결이 필요.
- 응답 시간(123ms, 89ms, 1500ms): 응답 시간이 기준을 초과하면 성능 최적화가 필요.

# 임계치

# 판단기준
- **양호**: 응답시간이 `max_response_time`을 초과하지 않는 상태(출력값 없는 상태)
- **경고**: 응답시간이 `max_response_time`을 초과한 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
