# 영역
로그

# 세부 점검항목
CPU 로그

# 점검 내용
CPU 에러로그 점검(Uncorrectable ECC Error, Offline)

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'ecc error|uncorrectable|cpu.*offline|offline.*cpu'
```

# 출력 결과
```text
(no output)
```

# 설명
- `dmesg` 로그에서 CPU 관련 ECC 오류, uncorrectable 오류, CPU offline 메시지를 확인한다.
- 해당 키워드가 발견되면 CPU 하드웨어, 시스템 보드, 펌웨어, 장애 로그를 추가 확인한다.
- 일시적인 메시지인지 반복 발생하는 장애인지 판단하기 위해 `/var/adm/syslog/syslog.log`도 함께 검토한다.
- 명령 결과가 없으면 해당 키워드가 확인되지 않은 상태로 본다.

# 임계치
cpu_bad_log_keywords

# 판단기준
- **양호**: CPU 관련 ECC, uncorrectable, offline 로그가 없는 경우
- **경고**: CPU 관련 ECC, uncorrectable, offline 로그가 확인되는 경우
- **확인 필요**: `dmesg` 실행 또는 로그 확인이 불가능한 경우
