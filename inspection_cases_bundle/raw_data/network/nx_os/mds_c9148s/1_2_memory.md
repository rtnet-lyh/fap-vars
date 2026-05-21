# 영역
자원 사용률

# 세부 점검항목
메모리 사용률

# 점검 내용
전체 메모리 크키 확인 및 사용량과 여유메모리 확인(여유메모리 10%권고)

# 구분
필수

# 명령어
```bash
show system resources
```

# 출력 결과
```text
CITS-SAN1# show system resources
Load average:   1 minute: 0.14   5 minutes: 0.15   15 minutes: 0.16
Processes   :   181 total, 1 running
CPU states  :   2.48% user,   4.47% kernel,   93.03% idle
        CPU0 states  :   2.00% user,   2.00% kernel,   96.00% idle
        CPU1 states  :   2.97% user,   6.93% kernel,   90.09% idle
Memory usage:   4155776K total,   795688K used,   3360088K free
Current memory status: OK



```

# 설명
- 명령어: CPU, 프로세스, 메모리 등 시스템 자원 사용상태 확인 명령어
- 'Memory usage:' 항목에서 전체 메모리 용량, 사용 중인 메모리, 여유 메모리를 확인 할 수 있음.
- 메모리 사용률(%) = used / total * 100

# 임계치
max_mem_usage_percent

# 판단기준
- **양호**: 메모리 사용률이 `max_mem_usage_percent` 이하인 상태
- **경고**: 메모리 사용률이 `max_mem_usage_percent` 초과인 상태
- **확인 필요**: 명령어 실패 및 'Memory usage:' 파싱 불가, Current memory status: OK가 아닌 경우.