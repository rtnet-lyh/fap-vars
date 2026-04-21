# 영역
CPU

# 세부 점검항목
CPU 코어별 상태 점검

# 점검 내용
가상 프로세서와 물리 CPU가 정상적으로 인식되고 모든 코어가 on-line 상태인지 점검합니다.

# 구분
필수

# 명령어
```bash
psrinfo -v
psrinfo -pv
```

# 출력 결과
```text
Status of virtual processor 0 as of 09/10/2024 12:34:56:
Processor has been on-line since 09/10/2024 12:00:00
Processor is part of the following processor set(s): 0

Status of virtual processor 1 as of 09/10/2024 12:34:56:
Processor has been on-line since 09/10/2024 12:00:00
Processor is part of the following processor set(s): 0

The physical processor has 2 virtual processors (0-1)
x86 (chipid 0x0001) 3000 MHz
Intel(r) Core(tm) i7-9700 CPU
```

# 설명
- 모든 가상 프로세서는 `Processor has been on-line since` 상태여야 정상입니다.
- `off-line` 상태가 있으면 코어 장애, 비활성화, 유지보수 상태 여부를 추가 점검해야 합니다.
- `psrinfo -pv` 출력으로 물리 CPU 수와 물리 CPU당 가상 프로세서 구성을 확인합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.
- `psrinfo -v`와 `psrinfo -pv`의 가상 프로세서 집계가 서로 맞지 않으면 구성 불일치로 실패 처리합니다.

# 임계치
- `max_offline_processor_count`: `0`
- `min_physical_processor_count`: `1`
- `expected_virtual_processor_count`: `0`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: 모든 가상 프로세서가 on-line이고 물리 CPU 수가 기준 이상인 경우
- **실패**: off-line 프로세서가 기준치를 초과하거나 물리/가상 CPU 수가 기대보다 적은 경우
- **실패**: `psrinfo` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
