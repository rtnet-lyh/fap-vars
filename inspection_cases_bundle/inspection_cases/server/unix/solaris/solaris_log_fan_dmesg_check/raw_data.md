# 영역
LOG

# 세부 점검항목
FAN 작동 이상 유무 점검

# 점검 내용
Solaris 커널 메시지에서 팬 과열, 회전 불가, 정상 작동 상태를 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'fan|fail'
```

# 출력 결과
```text
FAN1 failed: Over-temperature detected
Warning: FAN2 not spinning
FAN3 operational
```

# 설명
- 팬 과열 실패, 회전 불가, 정상 작동 여부를 확인합니다.
- `failed`, `not spinning` 메시지는 즉시 점검이 필요합니다.
- `operational` 단독 로그는 정상 정보로 간주합니다.

# 임계치
- `bad_log_keywords`: `failed,not spinning,over-temperature,fail`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: FAN 관련 로그가 없거나 정상 상태 정보만 있는 경우
- **실패**: `failed`, `not spinning`, `over-temperature` 같은 비정상 로그가 확인되는 경우
- **실패**: `dmesg | grep -i 'fan|fail'` 명령 실행 실패 시
