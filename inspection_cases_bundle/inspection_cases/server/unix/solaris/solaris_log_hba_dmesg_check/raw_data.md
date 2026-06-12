# 영역
LOG

# 세부 점검항목
HBA 작동 이상 유무 점검

# 점검 내용
Solaris 커널 메시지에서 HBA 루프 감지, 포트 offline/online 상태를 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'hba|loop|port|offline|online'
```

# 출력 결과
```text
HBA1: Loop detected on port 0
Port 1 offline due to error
HBA2: Port 2 online
```

# 설명
- HBA 루프 감지, 포트 offline/online 상태를 점검합니다.
- `offline`, `loop` 메시지는 포트 및 HBA 장치 점검이 필요합니다.
- `online` 단독 로그는 정상 정보로 간주합니다.

# 임계치
- `bad_log_keywords`: `loop,offline,error,failed,failure`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: HBA 관련 로그가 없거나 정상 online 정보만 있는 경우
- **실패**: `loop`, `offline`, `error` 같은 비정상 로그가 확인되는 경우
- **실패**: `dmesg | grep -i 'hba|loop|port|offline|online'` 명령 실행 실패 시
