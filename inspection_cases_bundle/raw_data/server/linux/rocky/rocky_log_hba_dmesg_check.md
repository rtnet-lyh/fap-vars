# 영역
로그

# 세부 점검항목
I/O 에러로그

# 점검 내용
입출력 작동 이상 유무 점검(통신 지연으로 인한 Timeout 발생 및 I/O Error, Transport Failed, Media Error)

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'i/o error\|timeout\|transport failed\|media error'
```

# 출력 결과
```text
[    2.215770] megaraid_sas 0000:01:00.0: FW provided TM TaskAbort/Reset timeout        : 0 secs/0 secs
```

# 설명
- `dmesg`에서 `timeout`, `I/O error`, `transport failed`, `media error` 계열 로그가 확인되면 디스크, HBA, RAID 컨트롤러, 케이블, 스토리지 경로 등 입출력 경로에서 지연 또는 장애가 발생했을 가능성이 있다.
- 예시의 `megaraid_sas` `TaskAbort/Reset timeout` 메시지는 RAID 컨트롤러 또는 연결된 디스크 장치 처리 과정에서 명령 중단, 리셋, 응답 지연이 발생했음을 의미할 수 있으므로 장치 상태와 컨트롤러 로그를 함께 확인한다.
- 장애 키워드가 검출되면 같은 시간대의 `/var/log/messages`, RAID 관리 도구 출력, 디스크 SMART 상태, HBA 또는 스토리지 이벤트 로그를 대조하여 단발성 메시지인지 반복 장애인지 판단한다.
- 현재 점검 스크립트는 임계치에 정의된 I/O 오류 키워드를 기준으로 `dmesg` 로그를 검색하고, 키워드가 하나 이상 검출되면 입출력 경로 장애 징후로 판정한다.

# 임계치
io_error_keywords: i/o error|timeout|transport failed|media error

# 판단기준
- **양호**: `dmesg | grep -i 'i/o error\|timeout\|transport failed\|media error'` 결과에서 `io_error_keywords`에 정의된 키워드가 검출되지 않는 경우
- **실패**: `dmesg | grep -i 'i/o error\|timeout\|transport failed\|media error'` 결과에서 `io_error_keywords`에 포함된 장애 키워드가 하나 이상 확인되는 경우
- **참고**: `grep` 결과가 없어서 명령 반환 코드가 1인 경우는 오류 로그 미검출로 보며, 명령 실행 오류와 구분한다.
