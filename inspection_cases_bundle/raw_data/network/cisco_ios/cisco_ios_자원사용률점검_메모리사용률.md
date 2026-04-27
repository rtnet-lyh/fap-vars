# 영역
NETWORK

# 세부 점검항목
메모리 사용률

# 점검 내용
라우터, 스위치 등의 네트워크 장비가 사용하는 메모리 사용률 확인

# 구분
필수

# 명령어
```text
show processes memory sorted
```

# 출력 결과
```text
Processor Pool Total:  786432000 Used: 421527552 Free: 364904448
      I/O Pool Total:   67108864 Used:   8454144 Free:  58654720

 PID TTY  Allocated      Freed    Holding    Getbufs    Retbufs Process
 123   0   65239120   10528472   43890576          0          0 IP Input
 265   0   43812096   13200240   30611856          0          0 ARP Input
  91   0   21592032    6041824   15550208          0          0 Hulc LED Process
```

# 설명
- `show processes memory sorted` 명령은 프로세서 메모리와 I/O 메모리의 총량, 사용량, 여유량을 확인하는 명령이다.
- `Processor Pool Total`, `Used`, `Free` 값을 기준으로 전체 메모리 사용률을 계산할 수 있다.
- `Holding` 값이 큰 프로세스가 장시간 유지되면 메모리 누수 또는 비정상 세션 증가 가능성을 의심할 수 있다.
- 메모리 여유가 부족하면 라우팅 업데이트 지연, 세션 처리 실패, 제어 평면 불안정으로 이어질 수 있어 원인 프로세스와 로그를 함께 확인해야 한다.

# 임계치
max_memory_usage_percent

# 판단기준
- **양호**: 계산된 메모리 사용률이 `max_memory_usage_percent` 이하이고 주요 프로세스의 Holding 값이 안정적인 경우
- **주의**: 메모리 사용률이 임계치에 근접하거나 특정 프로세스의 Holding 메모리가 빠르게 증가하는 경우
- **경고**: 메모리 사용률이 `max_memory_usage_percent`를 초과하거나 Free 메모리가 매우 낮아 서비스 영향이 우려되는 경우

