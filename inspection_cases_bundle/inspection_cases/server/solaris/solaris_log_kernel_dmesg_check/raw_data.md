# 영역
LOG

# 세부 점검항목
커널 로그

# 점검 내용
Solaris 커널 메시지에서 panic 관련 로그가 있는지 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'panic|kernel panic'
```

# 출력 결과
```text
Kernel panic: CPU context corrupt
Panic: Attempted to access invalid memory address
```

# 설명
- 커널 패닉 발생 이력을 확인하는 항목입니다.
- panic 관련 검색 결과가 한 줄이라도 있으면 실패로 처리합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.

# 임계치
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot`

# 판단기준
- **정상**: panic 관련 로그가 한 건도 없는 경우
- **실패**: panic 관련 로그가 한 건 이상 있거나 실행 오류 문구가 확인되는 경우
- **실패**: `dmesg | grep -i 'panic|kernel panic'` 명령 실행 실패 시
