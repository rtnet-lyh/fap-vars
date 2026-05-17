# 영역
로그

# 세부 점검항목
관리서버 로그 이상 유무 점검

# 점검 내용
Adminserver 로그 점검(엔진, 인스턴스 등에 관련된 매니지먼트 로그 점검)


# 구분
필수

# 명령어 - admin_log_path: /home/exTMS/tmax/jeus/log/adminServer
```bash
tail -f {{ admin_log_path }}/manager.log
```

# 출력 결과
```text

```

# 설명
- Log Level: 로그의 중요도를 나타내는 INFO, ERROR, WARN을 통해 상태를 파악할 수 있음. ERROR나 WARN 항목이 발생하면 확인 점검이 필요. 

# 임계치


# 판단기준 - 양호, 경고 수동 확인 필요
- **양호**: Timestamp, Event Source, Log Message에 이상이 없는 상태
- **경고**: Timestamp, Event Source, Log Message에 이상이 있는 상태
- **확인 필요**: 출력 및 로그파일이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
