# 영역
자원 사용률

# 세부 점검항목
메모리 사용률

# 점검 내용
메모리 사용률 확인

# 구분
필수

# 명령어
```bash

```

# 출력 결과
```text
falcon@Center_Server_J4300_A> show system memory
fpc0:
--------------------------------------------------------------------------
System memory usage distribution:
       Total memory: 2992128 Kbytes (100%)
    Reserved memory:   59052 Kbytes (  1%)
       Wired memory:  136476 Kbytes (  4%)
      Active memory: 1085592 Kbytes ( 36%)
    Inactive memory:   77940 Kbytes (  2%)
       Cache memory:  584704 Kbytes ( 19%)
        Free memory: 1047824 Kbytes ( 35%)
Memory disk resident memory:  400496 Kbytes
VM-Kbytes(  %  ) Resident(  %  ) Map-name
  1048576(99.99)   944772(90.10) kernel map
   524288(50.00)    48736(09.30) kmem map
     1216(00.12)     1216(99.99) exec map
    26212(02.50)     1092(04.17) pipe map
   115488(11.01)   114784(99.39) buffer map
    32768(03.13)    32768(99.99) pager map
Pid     VM-Kbytes(  %  ) Resident(  %  ) Process-name
      0         0(00.00)        0(00.00) [swapper]
      1         0(00.00)        0(00.00) /sbin/init --
      2         0(00.00)        0(00.00) [jfe_job_0_0]
      3         0(00.00)        0(00.00) [jfe_job_1_0]
---(more)---

```

# 설명
- 명령어: 시스템 메모리 분포와 사용 현황을 확인하는 명령어.
- Free memory는 현재 사용 가능한 여유량을 의미.
- 메모리 사용률(%) = 100% - Free memory(%)

# 임계치
max_mem_usage_percent

# 판단기준
- **양호**: 메모리 사용률이 `max_mem_usage_percent` 이하인 상태
- **경고**: 메모리 사용률이 `max_mem_usage_percent` 초과인 상태
- **확인 필요**: 명령어 실패 및 파싱 불가