# 영역
로그

# 세부 점검항목
WEB 서비스 불가 점검

# 점검 내용
WEB엔진, 어플리케이션 소스 오류 등으로 인한 WEB 서비스 자체 불가 확인 (500:Internal Server Error),사용자 폭주, 서버 상태 이상 시 발생

# 구분
필수

# 명령어

- error_log_path: /home/exTMS/tmax/webtob/log/main
```bash
grep "500" $(ls {{ error_log_path }}/error.log*|sort|tail -n 1)
```

# 출력 결과

(예방점검 예시와 다름, 명령어 확인 필요)
```text
[2026-05-12T13:32:07] [CLIENT(127.0.0.1)] [E] [ERR-00045] A request does not belong to any virtual host or node. Access is denied. {server address=127.0.0.1:9080, host:127.0.0.1} HEAD / HTTP/1.1
```

# 설명
- 500 상태 코드가 포함된 로그 항목은 서버 내부 오류를 의미하며, 오류가 발생한 경우, 서버나 애플리케이션 로그를 조사하여 근본적인 원인을 파악하고 수정 필요.

# 임계치

# 판단기준
- **양호**: 상태코드 500이 포함된 로그가 없는 상태
- **경고**: 상태코드 500이 포함된 로그가 있는 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
