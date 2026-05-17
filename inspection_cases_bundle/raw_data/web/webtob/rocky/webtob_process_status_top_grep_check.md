# 영역
프로세스

# 세부 점검항목
프로세스 사용 상태 점검

# 점검 내용
점유 리소스 사용률 점검

# 구분
필수

# 명령어

- process_name 변수 
```bash
top -b -n 1 | egrep "PID|{{ process_name }}" # 헤더 포함
```
```bash
top -b -n 1 | grep -E "{{ process_name }}" # 헤더 미포함
```

# 출력 결과
```text
[root@sd_tipswebwas ~]# top -b -n 1 | egrep "PID|exTMS"
    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
   4937 exTMS     20   0   89776   5716   4184 S   0.0   0.0   2:46.91 systemd
   4940 exTMS     20   0  301032   5496      0 S   0.0   0.0   0:00.00 (sd-pam)
   5029 exTMS     20   0   64484   3180   2680 S   0.0   0.0   0:00.00 dbus-daemon
1476176 exTMS     20   0 6052980 940596  30104 S   0.0   5.8  93:31.63 java
1480138 exTMS     20   0   19032   8728   8536 S   0.0   0.1   8:27.12 wsm
1480139 exTMS     20   0   12588    900    828 S   0.0   0.0   2:40.03 htl
1480140 exTMS     20   0 1211928 596944  10828 S   0.0   3.7   3:13.83 hth
3485909 exTMS     20   0  243244   6392   2628 S   0.0   0.0   0:12.54 tmux: server
3485910 exTMS     20   0  226432   4840   2716 S   0.0   0.0   0:00.01 bash
```

# 설명
- 리소스 사용률: 시스템 자원을 특정 프로세스가 얼마나 사용하고 있는지를 나타내는 비율이며, CPU 사용률(%CPU)과 메모리 사용률(%MEM)이 리소스 사용률로 언급됨. 위 예시에서는 프로세스가 CPU의 12.3%, 시스템 메모리의 2%를 사용하고 있음

# 임계치
ps_status: WebtoB 프로세스 상태(S)

# 판단기준
- **양호**: WebtoB 프로세스 상태(S)에 Z/T/D 상태가 포함되지 않은 상태
- **경고**: WebtoB 프로세스 상태(S)에 Z/T/D 상태가 포함된 상태
- **확인 필요**: 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못하는 상태
