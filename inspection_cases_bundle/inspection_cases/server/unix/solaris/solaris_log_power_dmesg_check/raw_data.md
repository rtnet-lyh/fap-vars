# 영역
LOG

# 세부 점검항목
전원공급장치 오류 및 이상 유무 점검

# 점검 내용
Solaris 커널 메시지에서 PSU 실패, 미감지, 전원공급장치 오류 여부를 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'psu|power supply|failed'
```

# 출력 결과
```text
PSU1 failed: Power supply unit error
Warning: Power supply unit PS2 not detected
Power supply unit PS3 operational
```

# 설명
- PSU 실패, 미감지, 정상 작동 상태를 확인합니다.
- 전원공급장치 관련 에러가 있으면 교체 또는 연결 점검이 필요합니다.
- `operational` 단독 로그는 정상 정보로 간주합니다.

# 임계치
- `bad_log_keywords`: `failed,not detected,error,fault,failure`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: PSU 관련 로그가 없거나 정상 상태 정보만 있는 경우
- **실패**: `failed`, `not detected`, `error`, `fault` 같은 비정상 로그가 확인되는 경우
- **실패**: `dmesg | grep -i 'psu|power supply|failed'` 명령 실행 실패 시
