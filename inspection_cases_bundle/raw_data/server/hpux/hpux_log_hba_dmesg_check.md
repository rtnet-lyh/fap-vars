# 영역
로그

# 세부 점검항목
HBA 로그

# 점검 내용
HBA 포트 및 SAN 연결 이상 로그를 점검한다.

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'hba.*(error|fail|failed)|loop detected|port.*offline|offline.*port|port.*online|online.*port'
```

# 출력 결과
```text
HBA1: Loop detected on port 0
Port 1 offline due to error
```

# 설명
- `dmesg` 로그에서 HBA 오류, loop detected, 포트 offline 메시지를 확인한다.
- `port online` 메시지는 정상 상태 또는 복구 상태로 간주한다.
- HBA 오류가 있으면 FC 케이블, SAN zoning, 스토리지 포트, HBA 드라이버 상태를 함께 확인한다.
- 지속적인 offline 또는 loop 오류는 스토리지 경로 장애로 이어질 수 있다.

# 임계치
hba_bad_log_keywords
hba_ignore_log_keywords

# 판단기준
- **양호**: HBA error, loop detected, port offline 로그가 없는 경우
- **경고**: HBA 오류 또는 포트 offline 관련 로그가 확인되는 경우
- **확인 필요**: 로그 확인이 불가능하거나 HBA 구성 여부가 불명확한 경우
