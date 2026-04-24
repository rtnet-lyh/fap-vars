# 영역
CPU

# 세부 점검항목
CPU 코어별 상태 점검

# 점검 내용
물리 CPU 및 프로세서 인스턴스의 정상 인식 여부를 점검한다.

# 구분
필수

# 명령어
```bash
ioscan -fnC processor
```

# 출력 결과
```text
Class       I  H/W Path        Driver      S/W State   H/W Type     Description
===========================================================================
processor  0  120             processor   CLAIMED     PROCESSOR    Processor
processor  1  121             processor   CLAIMED     PROCESSOR    Processor
processor  2  122             processor   CLAIMED     PROCESSOR    Processor
processor  3  123             processor   CLAIMED     PROCESSOR    Processor
```

# 설명
- `ioscan -fnC processor` 명령으로 HP-UX가 인식한 CPU 프로세서 장치 상태를 확인한다.
- `S/W State`가 `CLAIMED`이면 OS가 해당 프로세서를 정상 인식한 상태로 본다.
- 프로세서가 `UNCLAIMED`, `NO_HW`, `ERROR` 등으로 표시되면 하드웨어 장애 또는 드라이버/펌웨어 문제 가능성이 있다.
- 기대 CPU 수와 실제 인식 수가 다르면 장비 구성, 파티션 설정, 장애 로그를 함께 확인한다.

# 임계치
expected_cpu_count
allowed_processor_states

# 판단기준
- **양호**: 기대 CPU 수가 모두 확인되고 상태가 `CLAIMED`인 경우
- **경고**: CPU가 누락되었거나 `UNCLAIMED`, `NO_HW`, `ERROR` 상태가 있는 경우
- **확인 필요**: 기대 CPU 수 기준이 없거나 명령 실행 권한/환경 문제로 확인할 수 없는 경우
