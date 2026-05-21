# 영역
자원 사용률

# 세부 점검항목
CPU 사용률

# 점검 내용
프로세스 별 CPU 사용률 점검

# 구분
필수

# 명령어
```bash
show processes cpu sort
```

# 출력 결과
```text
CITS-SAN1# show processes cpu sort

CPU utilization for five seconds: 2%/0%; one minute: 7%; five minutes: 7%
PID    Runtime(ms)  Invoked   uSecs  5Sec    1Min    5Min    TTY  Process
-----  -----------  --------  -----  ------  ------  ------  ---  -----------
   10    802571040  1912885066      0   0.49%   0.43%  0.43%   -    events/1
 3423   1195535460  958243529      1   0.39%   0.36%  0.35%   -    lc_port_cfg
 3024   1475470700  284453012      5   0.29%   0.42%  0.42%   -    sysinfo
 3053    263537060  182925589      1   0.09%   0.02%  0.02%   -    SystemHealth
    1      2131890  37892949      0   0.00%   0.00%  0.00%   -    init
    2           10       263      0   0.00%   0.00%  0.00%   -    kthreadd
    3       608250  36913487      0   0.00%   0.00%  0.00%   -    migration/0


```

# 설명
- 명령어: 전체 CPU와 많이 사용하는 프로세스를 정렬하여 확인하는 명령어.
- 헤더의 5Sec/1Min/5Min는 각 5초,1분,5분 평균 CPU사용률이다.
- 5분 사용률 중에 임계치가 넘는 %가 있다면 취약으로 판단하면 될 것으로 보여진다.

# 임계치
max_cpu_usage_percent

# 판단기준
- **양호**: 각 프로세스의 5분 평균 CPU 사용률이 `max_cpu_usage_percent` 이하인 상태
- **경고**: 각 프로세스의 5분 평균 CPU 사용률이 `max_cpu_usage_percent` 초과인 상태
- **확인 필요**: 명령어 실패 및 5분 평균 CPU사용률 파싱 불가.