# 영역
LOG

# 세부 점검항목
메모리 오류 에러 로그 점검

# 점검 내용
Solaris 커널 메시지에서 메모리 ECC 오류와 정정 불가 오류를 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'ecc error|singlebit|multibit|uncorrectable'
```

# 출력 결과
```text
Single-bit ECC error detected on memory module 0
Multi-bit ECC error reported on memory bank 1
Uncorrectable ECC error found on memory slot 2
```

# 설명
- 단일비트/멀티비트 ECC 오류 및 정정 불가 오류를 확인합니다.
- 메모리 모듈, 뱅크, 슬롯 단위로 점검 및 교체 판단이 가능합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.

# 임계치
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: 메모리 ECC/uncorrectable 관련 로그가 한 건도 없는 경우
- **실패**: 관련 로그가 한 건 이상 있거나 실행 오류 문구가 확인되는 경우
- **실패**: `dmesg | grep -i 'ecc error|singlebit|multibit|uncorrectable'` 명령 실행 실패 시
