# 영역
DISK

# 세부 점검항목
디스크 I/O 상태 점검

# 점검 내용
디스크 I/O 지연 및 오류 징후를 점검한다.

# 구분
권고

# 명령어
```bash
sar -d 1 3
```

# 출력 결과
```text
HP-UX hpux01 B.11.31 U ia64  12/30/25

12:10:01   device    %busy   avque   r+w/s  blks/s  avwait  avserv
12:10:02   disk1        12     0.5      45    1024     1.2     4.5
12:10:03   disk1        18     0.7      62    1536     1.5     5.0
Average    disk1        15     0.6      53    1280     1.3     4.7
```

# 설명
- `sar -d 1 3` 명령으로 디스크별 I/O 사용률, 큐 길이, 서비스 시간을 확인한다.
- `%busy`, `avque`, `avwait`, `avserv` 값이 지속적으로 높으면 디스크 병목 또는 스토리지 지연 가능성이 있다.
- 단발성 피크보다 반복 발생 여부와 업무 시간대 패턴을 함께 확인한다.
- 장치 오류 여부는 `dmesg`, `/var/adm/syslog/syslog.log`, 스토리지 로그와 함께 판단한다.

# 임계치
DISK_BUSY_MAX_PCT
DISK_AVWAIT_MAX_MS
DISK_AVSERV_MAX_MS

# 판단기준
- **양호**: 디스크 사용률과 대기 시간이 임계치 이하이고 오류 로그가 없는 경우
- **경고**: `%busy`, `avwait`, `avserv`가 임계치를 지속 초과하거나 I/O 지연이 반복되는 경우
- **확인 필요**: `sar` 데이터가 없거나 디스크 장치 매핑이 불명확한 경우
