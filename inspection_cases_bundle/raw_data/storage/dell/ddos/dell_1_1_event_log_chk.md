# 영역
로그

# 세부 점검항목
EVENT 로그

# 점검 내용
에러 코드 (기동 및 정지 정상 유무, 운영 상태 및 각종 에러) 를 점검

# 구분
필수

# 명령어
```bash
alerts show current
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
sysadmin@localhost# alerts show current
Id      Post Time                  Severity   Class               Object   Message
-----   ------------------------   --------   -----------------   ------   -------------------------------------------------------
p0-96   Mon Mar 30 14:33:16 2026   ERROR      SystemMaintenance            EVT-SMTOOL-00001: Error communicating with mail server.
-----   ------------------------   --------   -----------------   ------   -------------------------------------------------------
There is 1 active alert.

```

# 설명
- 현재 시스템에 활성화된 Alert 및 Error 이벤트를 확인하는 명령어
- 시스템 운영 상태, 네트워크 장애, 서비스 오류, HW 이상 여부를 점검 가능
- Severity(ERROR/CRITICAL/WARNING) 기반으로 현재 장애 여부 확인 가능

# 임계치


# 판단기준
- **양호**: Active Alert가 없으며 Severity에 ERROR/CRITICAL 없는 상태
- **경고**: Active Alert(There is 1 active alert.)존재 또는 Severity에 ERROR/CRITICAL 존재하는 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
