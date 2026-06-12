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
dmesg
```

# 출력 결과
```text
[    0.000000] Linux version 5.14.0-611.13.1.el9_7.x86_64
[    1.234567] ata1: SATA link up 6.0 Gbps
[    2.345678] EXT4-fs (sda1): mounted filesystem with ordered data mode
[   15.456789] device-mapper: multipath: version 1.14.0 loaded
[  120.567890] Out of memory: Killed process 1234 (java) total-vm:1048576kB
[  180.678901] blk_update_request: I/O error, dev sda, sector 123456
[  181.789012] Buffer I/O error on dev sda1, logical block 15432
[  250.890123] CPU0: Core temperature above threshold, cpu clock throttled
```

# 설명
- `dmesg` 명령은 시스템 부팅 이후 커널 메시지 버퍼에 기록된 로그를 확인하기 위한 명령이다.
- 본 항목은 시스템, 커널, 메모리, 디스크 I/O, 장치 인식, 드라이버, 파일시스템 관련 로그를 점검하여 장치 및 인스턴스, 서비스 이상 유무를 확인하기 위한 항목이다.
- 특히 `I/O error`, `Buffer I/O error`, `Out of memory`, `Call Trace`, `segfault`, `filesystem error` 와 같은 메시지는 장애 또는 성능 저하의 주요 징후가 될 수 있다.
- 일시적인 정보성 메시지와 실제 오류 메시지를 구분하여 확인해야 하며, 동일 오류가 반복되거나 최근에도 지속적으로 발생하는 경우 원인 분석이 필요하다.
- 커널 로그에서 하드웨어 장애, 메모리 부족, 디스크 오류, 드라이버 이상이 확인되면 관련 장치 점검 및 서비스 영향도 분석을 권고한다.

# 임계치
critical_log_keywords
warning_log_keywords

# 판단기준
- **양호**: `dmesg` 출력에서 임계치에 정의된 치명적 오류 키워드가 존재하지 않고, 경고 수준 메시지도 반복적으로 확인되지 않는 상태
- **주의**: 임계치에 정의된 경고 키워드가 존재하거나, 장치/서비스 관련 경고성 로그가 산발적으로 확인되는 상태
- **경고**: 임계치에 정의된 치명적 오류 키워드가 존재하거나, 메모리 부족, 디스크 I/O 오류, 파일시스템 오류, 커널 패닉 관련 로그가 확인되는 상태
- **참고**: 판단기준 적용을 위해 임계치에는 반드시 `critical_log_keywords`, `warning_log_keywords` 와 같이 점검 대상 키워드 목록이 정의되어 있어야 함