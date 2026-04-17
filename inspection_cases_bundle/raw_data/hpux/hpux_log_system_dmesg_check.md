# 영역
로그

# 세부 점검항목
시스템 로그

# 점검 내용
장치 및 인스턴스가 서비스를 하고 있지만 성능이 저하되거나 손실될 우려 여부 점검

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'error|fail|warning'
```

# 출력 결과
```text
WARNING: SCSI: Disk queue depth adjusted for /dev/dsk/c2t0d0
ERROR: fscsi0: I/O error detected on target 0 lun 0
```

# 설명
- `dmesg` 로그에서 error, fail, warning 키워드를 확인하여 시스템 장치와 서비스 이상 징후를 점검한다.
- 경고성 메시지는 일시적 정보와 실제 장애 징후를 구분해야 한다.
- I/O 오류, 장치 장애, 드라이버 오류, 반복 경고가 확인되면 관련 장치와 서비스 영향도를 분석한다.
- 필요 시 `/var/adm/syslog/syslog.log`와 하드웨어 이벤트 로그를 함께 확인한다.

# 임계치
system_bad_log_keywords
system_ignore_log_keywords

# 판단기준
- **양호**: 장애성 error, fail, warning 로그가 확인되지 않는 경우
- **주의**: 경고성 로그가 산발적으로 확인되나 서비스 영향이 명확하지 않은 경우
- **경고**: 오류 또는 실패 로그가 반복되거나 장치 장애 징후가 확인되는 경우
