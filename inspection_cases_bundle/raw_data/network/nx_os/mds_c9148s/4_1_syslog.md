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
show logging | include fail|error|warning|stop|down
```

# 출력 결과
```text
CITS-SAN1# show logging | include fail|error|warning|stop|down
3(errors)               4(warnings)     5(notifications)
2026 Mar 27 09:46:04 CITS-SAN1 %PORT-5-IF_DOWN_LINK_FAILURE: %$VSAN 10%$ Interface fc1/5 is down (Link failure loss of signal)
2026 Apr 15 15:47:57 CITS-SAN1 %AUTHPRIV-3-SYSTEM_MSG: pam_aaa:Authentication failed from console - login
2026 May 19 17:00:17 CITS-SAN1 %AUTHPRIV-3-SYSTEM_MSG: pam_aaa:Authentication failed from 172.18.8.191 - sshd[21938]
2026 May 20 17:44:48 CITS-SAN1 %AUTHPRIV-3-SYSTEM_MSG: pam_aaa:Authentication failed from 172.18.8.191 - sshd[13859]

```


# 설명
- 명령어: 장비에 기록된 시스템 로그를 확인하는 명령어.
- include 옵션으로 특정 문자 파싱: fail|error|warning|stop|down

[참고]
- 변수로 파싱할 문자를 선언하는 방향도 있음.

# 임계치

# 판단기준
- **양호**: 결과 값 미 출력
- **경고**: 결과 값 출력
- **확인 필요**: 명령어 실패