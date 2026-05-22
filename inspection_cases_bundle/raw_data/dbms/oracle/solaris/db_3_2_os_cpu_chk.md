# 영역
OS 리소스 사용률

# 세부 점검항목
물리적 CPU 사용률

# 점검 내용
DB 기동중인 상태에서 물리적 CPU 사용률 상태가 적절한 수치를 유지하는지 점검

# 구분
필수

# 명령어
```bash
ps -eo pid,comm,pcpu | grep ora_
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ ps -eo pid,comm,pcpu | grep ora_
 1004 ora_diag_TTIPS1                                                                   0.0
 1058 ora_dbw6_TTIPS1                                                                   0.0
 3442 ora_p000_TTIPS1                                                                   0.0
 1028 ora_lms3_TTIPS1                                                                   0.1
 1014 ora_ping_TTIPS1                                                                   0.0
  999 ora_gen0_TTIPS1                                                                   0.0
 1011 ora_dbrm_TTIPS1                                                                   0.1
 1023 ora_lms0_TTIPS1                                                                   0.2
```

# 설명
- %CPU: 프로세스가 사용하는 CPU 사용률임. 해당 프로세스가 사용하는 CPU 비율을 나타내며, 이 수치를 통해 CPU 사용량이 적절한지 확인할 수 있음. CPU 사용률이 지나치게 높은 경우 시스템 성능 저하가 발생할 수 있으므로 주기적으로 확인하여 적절한 사용 상태를 유지해야 함.

# 임계치
max_cpu_usage_percent: CPU 사용률 임계치 최대값(ex.70%)

# 판단기준
- **양호**: %CPU값이 `max_cpu_usage_percent`를 넘지 않는 상태의 프로세스
- **경고**: %CPU값이 `max_cpu_usage_percent`를 넘지 상태의 프로세스
- **확인 필요**: 대상 프로세스가 없거나 명령어 출력값이 없는 상태
