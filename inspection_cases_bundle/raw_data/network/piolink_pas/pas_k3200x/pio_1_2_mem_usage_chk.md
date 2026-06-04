# 영역
자원 사용률

# 세부 점검항목
메모리 사용률

# 점검 내용
라우터, 스위치 등의 네트워크 장비가 사용하는 메모리 사용률 확인

# 구분
필수

# 명령어
```bash
show resource
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show resource
================================================================================
  RESOURCE
--------------------------------------------------------------------------------
    Management Processor
        CPU
                Usage     : 2.43%

        Memory
                Total     : 1572864 kB
                Used      : 443092 kB
                Free      : 1129772 kB
                Usage     : 28.17%

    Packet Processor
        CPU
                Usage     : 2.68%

        Memory
                Total     : 14518804 kB
                Used      : 2134320 kB
                Free      : 12384484 kB
                Usage     : 14.70%

    Log Storage
                Total     : 218043 MB
                Used      : 1650 MB
                Free      : 205316 MB
                Usage     : 1%
================================================================================

```

# 설명
- Memory Usage : 메모리 자원 사용률

# 임계치
max_used_percent: 파일시스템 최대 사용률

# 판단기준
- **양호**: Memory Usage 값이 `max_used_percent`를 초과하지 않는 상태
- **경고**: Memory Usage 값이 `max_used_percent`를 초과한 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
