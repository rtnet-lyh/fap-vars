# 영역
LOG

# 세부 점검항목
NIC 정상 유무 점검

# 점검 내용
Solaris 커널 메시지에서 NIC 링크 다운, failover, 상태 변화를 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'nic|link|failover|status|down'
```

# 출력 결과
```text
NIC0: Link Down
NIC1: IPMP failover occurred on interface
NIC2: Status Up
NIC3: Link Down
```

# 설명
- NIC 링크 다운, IPMP failover, 상태 정상 여부를 확인합니다.
- `Link Down` 또는 failover 빈발 시 케이블/포트/NIC 점검이 필요합니다.
- `Status Up` 단독 로그는 정상 정보로 간주합니다.

# 임계치
- `bad_log_keywords`: `link down,failover,down,error,failed`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: NIC 관련 로그가 없거나 정상 up 정보만 있는 경우
- **실패**: `Link Down`, `failover`, `error` 같은 비정상 로그가 확인되는 경우
- **실패**: `dmesg | grep -i 'nic|link|failover|status|down'` 명령 실행 실패 시
