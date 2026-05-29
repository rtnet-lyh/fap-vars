# 영역
로그

# 세부 점검항목
시스템 로그

# 점검 내용
HW 상태와 관련된 ERROR 로그(Fail, Error, Warning, Stop, Down) 발생 여부 점검

# 구분
필수

# 명령어
```bash
show log messages | match "fail|error|warning|stop|down"
```

# 출력 결과
```text
falcon@Center_Server_J4300_B> show log
                                   ^
syntax error, expecting <command>.

```


# 설명
- 명령어: 장비에 기록된 시스템 로그를 확인하는 명령어.
- 권한문제로 인한 로그 확인 불가


# 임계치

# 판단기준
- **양호**: 결과 값 미 출력
- **경고**: 결과 값 출력
- **확인 필요**: 명령어 실패