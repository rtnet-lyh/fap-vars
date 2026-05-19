# 영역
로그

# 세부 점검항목
에러 로그 점검

# 점검 내용
웹서버 엔진 자체적으로 서비스 요청, 응답, 내부처리 등에 문제가 발생 시 출력하는 로그로 특이사항 점검

# 구분
필수

# 명령어 - error_log_path: /home/exTMS/tmax/webtob/log/main
```bash
grep "error" $(ls {{ error_log_path }}/error.log*|sort|tail -n 1)
```

# 출력 결과 (예방점검 예시와 다름, 명령어 확인 필요)
```text
[2026-05-12T13:32:07] [CLIENT(127.0.0.1)] [E] [ERR-00045] A request does not belong to any virtual host or node. Access is denied. {server address=127.0.0.1:9080, host:127.0.0.1} HEAD / HTTP/1.1
```

# 설명
- 에러 로그를 통해 웹 서버의 문제를 식별하며, 특히 ERROR 레벨의 로그와 구체적인 에러 메시지를 통해 문제의 심각성을 판단함. 최근 로그를 검토하고, CRITICAL 및 FATAL 에러는 즉시 대응이 필요.


# 임계치

# 판단기준
- **양호**: CRITICAL 및 FATAL 에러가 없는 상태
- **경고**: CRITICAL 및 FATAL 에러가 있는 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
