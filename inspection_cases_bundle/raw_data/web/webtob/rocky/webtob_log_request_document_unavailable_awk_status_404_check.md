# 영역
로그

# 세부 점검항목
요청 문서 처리 불가 점검

# 점검 내용
사용자(클라이언트)가 요청한 문서 또는 웹페이지를 찾을 수 없는 상태(404:Not Found), 소스 위치 변경 또는 삭제된 문서(웹페이지 포함)에서 발생

# 구분
필수

# 명령어

- access_log_path: /home/exTMS/tmax/webtob/log/main
```bash
awk '$(NF-2)=404' $(ls {{ access_log_path }}/access.log*|sort|tail -n 1) | tail -20
```

# 출력 결과
```text
[root@tips_web1 main]# awk '$(NF-2)=404' $(ls /home/exTMS/tmax/webtob/log/main/access.log*|sort|tail -n 1) | tail -20
172.29.41.55 [08/May/2026:17:53:55 +0900] "POST /getOpinionPopupInfo.do HTTP/1.1" 404 12 6
172.25.37.142 [08/May/2026:17:53:55 +0900] "POST /getLtrsInfoList.do HTTP/1.1" 404 991 18
172.34.41.60 [08/May/2026:17:53:55 +0900] "POST /getVmsAutoTargetDrfInfo.do HTTP/1.1" 404 5418 21
172.29.41.55 [08/May/2026:17:53:55 +0900] "POST /checkSession.do HTTP/1.1" 404 14 4
```

# 설명
- 자주 발생하는 404 오류는 웹 페이지나 문서의 실제 위치를 검토하고, 링크가 올바르게 설정되었는지 확인하거나 삭제된 페이지에 대해 적절한 대체 페이지를 제공하는 것이 필요

# 임계치

# 판단기준
- **양호**: 응답시간이 `max_response_time`을 초과하지 않는 상태
- **경고**: 응답시간이 `max_response_time`을 초과한 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
