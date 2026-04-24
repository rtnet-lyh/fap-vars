# 영역
로그

# 세부 점검항목
커널로그

# 점검 내용
하드웨어 이상으로 인한 커널 패닉로그 점검(Kernel Panic, Panicking)

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'panic|kernel panic|panicking'
```

# 출력 결과
```text
(no output)
```

# 설명
- `dmesg` 로그에서 kernel panic, panic, panicking 관련 메시지를 확인한다.
- 커널 패닉 로그가 확인되면 crash dump, GSP/MP 로그, syslog, 최근 변경 작업을 함께 검토한다.
- 실제 패닉이 발생한 경우 재부팅 이력과 서비스 영향이 있었는지 확인한다.
- 명령 결과가 없으면 해당 키워드가 확인되지 않은 상태로 본다.

# 임계치
kernel_panic_keywords

# 판단기준
- **양호**: 커널 패닉 관련 로그가 없는 경우
- **경고**: kernel panic, panic, panicking 로그가 확인되는 경우
- **확인 필요**: `dmesg` 또는 관련 로그를 확인할 수 없는 경우
