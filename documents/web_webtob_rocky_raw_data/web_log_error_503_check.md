# 영역
로그

# 세부 점검항목
서비스 제공 불가 점검

# 점검 내용
사용자(클라이언트) 요청에 통신오류 서비스 불가와 비슷하게 WEB 서버가 응답하지 못해 발생(503:Service Temporary Unavailable), 서버 HW 자원사용률 과부하 또는 접속자 폭주 등으로 발생

# 구분
필수

# 명령어 - error_log_path: /home/exTMS/tmax/webtob/log/main
```bash
grep "503" $(ls {{ error_log_path }}/error.log*|sort|tail -n 1)
```

# 출력 결과 (예방점검 예시와 다름, 명령어 확인 필요)
```text
[2026-05-12T13:32:07] [CLIENT(127.0.0.1)] [E] [ERR-00045] A request does not belong to any virtual host or node. Access is denied. {server address=127.0.0.1:9080, host:127.0.0.1} HEAD / HTTP/1.1
```

# 설명
- 503 상태 코드는 웹 서버가 일시적으로 서비스를 제공할 수 없는 상태를 의미하며, 서버 자원 부족이나 과부하로 인해 발생함. 이 오류가 발생할 경우, 서버 자원과 설정을 점검하여 문제를 해결하는 것이 필요하며, 빈번한 경우 성능 개선 조치 권고.

# 임계치

# 판단기준
- **양호**: 상태코드 503이 포함된 로그가 없는 상태
- **경고**: 상태코드 503이 포함된 로그가 있는 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
