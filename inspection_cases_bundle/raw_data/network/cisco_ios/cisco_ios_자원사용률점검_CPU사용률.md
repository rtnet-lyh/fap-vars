# 영역
NETWORK

# 세부 점검항목
CPU 사용률

# 점검 내용
라우터, 스위치 등의 네트워크 장비가 사용하는 CPU자원 사용률 확인

# 구분
필수

# 명령어
```text
show processes cpu sorted
```

# 출력 결과
```text
CPU utilization for five seconds: 18%/4%; one minute: 12%; five minutes: 10%
 PID Runtime(ms)   Invoked      uSecs   5Sec   1Min   5Min TTY Process
 123    950932     152349       6243    6.5%   5.8%   5.4%   0 IP Input
 265    412540      82341       5010    3.4%   2.9%   2.8%   0 ARP Input
  91    215336     111928       1923    1.2%   0.9%   0.8%   0 Hulc LED Process
```

# 설명
- `show processes cpu sorted` 명령은 Cisco IOS 장비의 전체 CPU 사용률과 CPU 점유율이 높은 프로세스를 함께 확인하는 기본 명령이다.
- `five seconds`, `one minute`, `five minutes` 값은 각각 단기 순간 부하와 평균 부하를 보여준다.
- `18%/4%` 형식에서 앞의 값은 전체 CPU 사용률이고 뒤의 값은 인터럽트가 사용하는 비율이다.
- 특정 프로세스가 지속적으로 상단에 나타나거나 5분 평균 CPU 사용률이 높게 유지되면 제어 평면 부하, 라우팅 갱신 과다, 브로드캐스트 폭주 여부를 함께 점검한다.

# 임계치
max_cpu_usage_percent

# 판단기준
- **양호**: 5분 평균 CPU 사용률이 `max_cpu_usage_percent` 이하이고 특정 프로세스의 과도한 점유가 없는 경우
- **주의**: 5초 또는 1분 CPU 사용률이 일시적으로 높지만 5분 평균은 임계치 이하인 경우
- **경고**: 5분 평균 CPU 사용률이 `max_cpu_usage_percent`를 초과하거나 특정 프로세스가 지속적으로 높은 CPU를 점유하는 경우

