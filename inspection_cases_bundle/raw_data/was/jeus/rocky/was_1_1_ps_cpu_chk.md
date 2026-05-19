# 영역
프로세스

# 세부 점검항목
프로세스 CPU 사용률

# 점검 내용
WAS 서비스 부하 확인을 위한 WAS 프로세스가 사용하고 있는 CPU 자원 사용률 확인

# 구분
필수

# 명령어 - process_name 변수 
```bash
top -b -n 1 | egrep "PID|{{ process_name }}" # 헤더 포함
```
```bash
top -b -n 1 | grep -E "{{ process_name }}" # 헤더 미포함
```

# 출력 결과
```text
[root@tips_was1 jeus]# top -b -n 1 | egrep "PID|exTMS"
    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 419081 exTMS     20   0   11.5g   2.6g  34080 S   6.2  11.1 402:35.78 java
   1715 exTMSagn  20   0   89852   9564   8176 S   0.0   0.0   0:39.25 systemd
   1744 exTMSagn  20   0  153960   4064      4 S   0.0   0.0   0:00.00 (sd-pam)
   1931 exTMSagn  20   0 5088156 290296  17504 S   0.0   1.2  65:25.02 java
   2366 exTMSagn  20   0   64484   4932   4612 S   0.0   0.0   0:00.00 dbus-da+
 738307 exTMS     20   0   15.6g   8.9g  33672 S   0.0  38.1 397:00.07 java
1150460 exTMS     20   0   89872   9944   8320 S   0.0   0.0   0:29.51 systemd
1150464 exTMS     20   0  301424   4456      4 S   0.0   0.0   0:00.00 (sd-pam)
1150575 exTMS     20   0   64484   5424   4920 S   0.0   0.0   0:00.00 dbus-da+
1151048 exTMS     20   0  243708   5316   2884 S   0.0   0.0   0:03.28 tmux: s+
1151049 exTMS     20   0  226456   3484   3480 S   0.0   0.0   0:00.02 bash
1158057 exTMS     20   0 8012564 845004  27620 S   0.0   3.5 127:58.28 java
1158123 exTMS     20   0  222604   3092   3092 S   0.0   0.0   0:00.00 startNo+
1158124 exTMS     20   0 4969008 167684  19060 S   0.0   0.7  83:03.42 java
```

# 설명
- %CPU : 프로세스가 사용하는 CPU 사용률을 나타냄

# 임계치
max_cpu_usage_percent: CPU 사용률 임계치 최대값(ex.70%)

# 판단기준
- **양호**: CPU 사용률이 `max_cpu_usage_percent` 이하인 상태
- **경고**: CPU 사용률이 `max_cpu_usage_percent`를 초과하여 CPU 부하가 높은 상태
- **확인 필요**: 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못하는 상태
