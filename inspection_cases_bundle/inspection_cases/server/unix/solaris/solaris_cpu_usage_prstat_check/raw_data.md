# 영역
CPU

# 세부 점검항목
CPU 사용률

# 점검 내용
Solaris 서버의 시스템 전체 CPU 사용률과 상위 프로세스 CPU 사용률을 함께 점검합니다.

# 구분
필수

# 명령어
```bash
prstat 1
mpstat 1 1
```

# 출력 결과
```text
   PID USERNAME  SIZE   RSS STATE  PRI NICE      TIME  CPU PROCESS/NLWP
 18452 oracle   1536M 1024M sleep   59    0   0:01:12  4.8 dbwriter/12
 18460 oracle    640M  512M sleep   59    0   0:00:54  2.1 lgwr/4
  2331 root      120M   64M sleep   99    0   0:00:08  1.2 sshd/1
Total: 275 processes, 512 lwps, load averages: 0.42, 0.38, 0.31

CPU minf mjf xcal intr ithr  csw icsw migr smtx  srw syscl  usr sys  wt idl
  0   20   0    1  150  120  220   15    3    0    0   310   18   6   4  72
  1   18   0    1  140  110  210   14    4    0    0   300   16   5   3  76
```

# 설명
- `prstat 1`은 상위 프로세스의 CPU 점유율을 확인할 때 사용합니다. replay에서는 1회 측정을 위해 `prstat 1 1` 형태로 사용합니다.
- `mpstat 1 1`은 CPU별 `usr`, `sys`, `wt`, `idl` 값을 보여주며 시스템 전체 CPU 사용률은 `100 - idl`로 계산합니다.
- 상위 프로세스 `%CPU`가 과도하거나 시스템 전체 CPU 사용률이 높으면 배치 작업, runaway process, I/O wait 여부를 함께 확인해야 합니다.
- `prstat`, `mpstat` 명령이 없거나 출력 형식을 해석할 수 없으면 실패로 처리합니다.

# 임계치
- `max_cpu_usage_percent`: `70`
- `max_process_cpu_percent`: `5`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 시스템 전체 CPU 사용률이 `max_cpu_usage_percent` 이하이고, 최고 프로세스 CPU 사용률이 `max_process_cpu_percent` 이하인 경우
- **실패**: 시스템 전체 CPU 사용률 또는 최고 프로세스 CPU 사용률이 기준치를 초과한 경우
- **실패**: `prstat` 또는 `mpstat` 명령 실행 실패, 명령 미설치, 출력 파싱 실패, 오류 로그 확인 시
