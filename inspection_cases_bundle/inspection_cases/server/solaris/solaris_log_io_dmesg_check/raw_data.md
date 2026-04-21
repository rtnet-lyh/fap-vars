# 영역
LOG

# 세부 점검항목
입출력 작동 이상 유무 점검

# 점검 내용
Solaris 커널 메시지에서 I/O 오류, 타임아웃, 전송 실패, 미디어 오류를 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'timeout|i/o error|transport failed|media error'
```

# 출력 결과
```text
I/O Error: Device /dev/sda1 reported error
Timeout occurred while waiting for device
Transport failed for SCSI device /dev/sdb
Media error detected on /dev/sdc
```

# 설명
- I/O 오류, 타임아웃, 전송 실패, 미디어 에러를 확인합니다.
- 스토리지 장치 상태와 연결 경로를 함께 점검해야 합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.
- `grep` 특성상 일치 로그가 없으면 `rc=1`이 반환될 수 있으며, 이 경우는 정상으로 처리합니다.

# 임계치
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: I/O 오류 관련 로그가 한 건도 없는 경우
- **실패**: 관련 로그가 한 건 이상 있거나 실행 오류 문구가 확인되는 경우
- **실패**: `stderr`가 있거나 `dmesg | grep -i 'timeout|i/o error|transport failed|media error'` 명령 실행 실패 시
