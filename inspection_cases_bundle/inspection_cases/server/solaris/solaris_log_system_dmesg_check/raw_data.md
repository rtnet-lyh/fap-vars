# 영역
LOG

# 세부 점검항목
시스템 로그

# 점검 내용
Solaris 커널 메시지에서 장치 오류와 일반 경고 로그가 있는지 점검합니다.

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'error|fail|warning'
```

# 출력 결과
```text
Error: Device sda1 failure detected
Warning: Disk space low on /dev/sdb
Fail: Network interface eth0 down
```

# 설명
- 장치 오류, 디스크 공간 부족, 네트워크 인터페이스 다운 여부를 확인합니다.
- 검색 결과가 한 줄이라도 있으면 장애 가능성이 있으므로 실패로 처리합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.

# 임계치
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot`

# 판단기준
- **정상**: `error`, `fail`, `warning` 패턴 로그가 한 건도 없는 경우
- **실패**: 검색 결과가 한 건 이상 있거나 실행 오류 문구가 확인되는 경우
- **실패**: `dmesg | grep -i 'error|fail|warning'` 명령 실행 실패 시
