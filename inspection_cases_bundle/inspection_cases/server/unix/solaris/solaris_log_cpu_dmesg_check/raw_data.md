# 영역
LOG

# 세부 점검항목
CPU 로그

# 점검 내용
Solaris 커널 메시지에서 CPU 하드웨어 오류 관련 로그가 있는지 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'ecc error|uncorrectable|offline'
```

# 출력 결과
```text
ECC error detected on CPU0
Uncorrectable ECC error on CPU1
CPU2 offline due to hardware failure
```

# 설명
- ECC 오류, 정정 불가 오류, CPU offline 상태를 확인합니다.
- 검색 결과가 한 줄이라도 있으면 CPU 하드웨어 이상 가능성이 있으므로 실패로 처리합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.

# 임계치
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot`

# 판단기준
- **정상**: CPU 오류 관련 로그가 한 건도 없는 경우
- **실패**: CPU 오류 관련 로그가 한 건 이상 있거나 실행 오류 문구가 확인되는 경우
- **실패**: `dmesg | grep -i 'ecc error|uncorrectable|offline'` 명령 실행 실패 시
