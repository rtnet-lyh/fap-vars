# 영역
CPU

# 세부 점검 항목
CPU 사용률 및 Idle/Interrupt 비율

# 점검 내용
typeperf로 3회 샘플링하여 사용자+커널 사용률, Idle 비율, Interrupt 비율의 평균을 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); typeperf "\\Processor(_Total)\\% User Time" "\\Processor(_Total)\\% Privileged Time" "\\Processor(_Total)\\% Idle Time" "\\Processor(_Total)\\% Interrupt Time" -sc 3 -si 1
```

# 출력 결과
```text
"(PDH-CSV 4.0)","\\HOST\\Processor(_Total)\\% User Time","\\HOST\\Processor(_Total)\\% Privileged Time","\\HOST\\Processor(_Total)\\% Idle Time","\\HOST\\Processor(_Total)\\% Interrupt Time"
"04/10/2026 15:45:24.602","5.19","16.54","76.89","1.15"
"04/10/2026 15:45:25.606","5.04","13.00","78.56","0.77"
```

# 설명
- 평균 `usr+sys` 비율, 평균 idle 비율, 평균 interrupt 비율을 계산합니다.
- 순간값이 아닌 3회 평균을 사용해 일시적인 스파이크를 줄여 해석합니다.

# 임계치
- `max_usr_sys_percent`: `80.0`
- `min_idle_percent`: `20.0`
- `max_interrupt_percent`: `5.0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 평균 CPU 사용률은 낮고 idle 비율은 충분하며 interrupt 비율도 임계치 이하입니다.
- **경고**: 평균 `usr+sys`가 높거나 idle 비율이 부족하거나 interrupt 비율이 과도합니다.


