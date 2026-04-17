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
dmesg | grep -i 'panic'
```

# 출력 결과
```text
[  245.678901] Kernel panic - not syncing: Fatal hardware error!
[  245.679120] CPU: 3 PID: 1024 Comm: kworker/3:1 Not tainted 5.14.0-611.13.1.el9_7.x86_64
[  245.679845] Hardware name: ExampleServer R650/1.0, BIOS 2.8.4 11/15/2025
[  245.680512] Call Trace:
[  245.681033]  <TASK>
[  245.681420]  panic+0x110/0x2f0
[  245.681955]  machine_check_poll+0x1b4/0x220
[  245.682604]  do_machine_check+0x7d0/0x900
[  245.683210]  exc_machine_check+0x7a/0xd0
[  245.683834] Kernel Offset: disabled
```

# 설명
- (커널 패닉 메시지) Kernel panic 메시지가 확인되면, 커널 로그 분석과 시스템 재부팅 후 상태 점검 필요
- (CPU 및 프로세스 정보) CPU와 프로세스 정보를 확인하고, 상세 분석 권고
- (하드웨어 정보) 하드웨어 모델 정보를 확인하고, 하드웨어 상태 점검 권고
- (콜 트레이스) 호출 트레이스를 분석하여 패닉 원인을 파악하고, 커널 패치나 설정 변경 필요

# 임계치

# 판단기준
- **양호**: `dmesg | grep -i 'panic'` 결과에서 임계치에 정의된 패닉 키워드가 존재하지 않는 상태
- **실패**: 패닉 키워드 존재