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
dmesg | grep -Fi <동적 생성된 -e fail_keyword 목록>
```

기본 임계치 기준 생성 예시:

```bash
dmesg | grep -Fi -e 'i/o error' -e timeout -e 'transport failed' -e 'media error'
```

# 출력 결과
```text
[    2.215770] megaraid_sas 0000:01:00.0: FW provided TM TaskAbort/Reset timeout        : 0 secs/0 secs
```

# 설명
- 본 항목은 `dmesg` 커널 로그에서 디스크, HBA, RAID 컨트롤러, 스토리지 경로와 관련된 I/O 오류 및 timeout 징후를 확인한다.
- 점검 스크립트는 `io_error_fail_keywords` 값을 `|` 기준으로 분리한 뒤 각 키워드를 `grep -Fi -e '<keyword>'` 인자로 붙여 명령어를 동적으로 생성한다.
- 예시의 `megaraid_sas` `TaskAbort/Reset timeout` 메시지는 RAID 컨트롤러 또는 연결된 디스크 장치 처리 과정에서 명령 중단, 리셋, 응답 지연이 발생했을 가능성을 의미한다.
- fail 키워드가 포함된 후보 로그 중 `io_error_except_keywords`에 해당하는 라인은 제외하고, 제외 후 남은 로그가 하나 이상이면 I/O 장애 징후로 판정한다.
- 장애 로그가 확인되면 같은 시간대의 `/var/log/messages`, RAID 관리 도구 출력, 디스크 SMART 상태, HBA 또는 스토리지 이벤트 로그를 함께 확인하여 단발성 메시지인지 반복 장애인지 판단한다.

# 임계치
io_error_fail_keywords: i/o error|timeout|transport failed|media error
io_error_except_keywords: hung_task_timeout_secs|rcu:|watchdog

# 판단기준
- **양호**: fail 키워드가 포함된 후보 로그가 없거나, 후보 로그가 모두 `io_error_except_keywords`에 의해 제외되는 경우
- **실패**: fail 키워드가 포함된 로그 중 `io_error_except_keywords`로 제외되지 않은 로그가 하나 이상 확인되는 경우
- **참고**: `grep` 결과가 없어서 명령 반환 코드가 1인 경우는 오류 로그 미검출로 보고, 명령 실행 오류와 구분한다.
- **참고**: `timeout`은 I/O 외 다른 커널 메시지에도 포함될 수 있으므로 except 임계치로 비 I/O성 timeout 로그를 분리한다.
