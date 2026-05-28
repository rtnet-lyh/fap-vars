# 영역
서비스  

# 세부 점검항목
각 LB 상태 확인

# 점검 내용
부하 분산 상태 점검 및 real 서버 Health-Check 상태 점검

# 구분
권고

# 명령어
```bash
show real
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show real

================================================================================
REAL Configuration
 ------------------------------------------------------------------------------
  ID    Name            RIP         Rport SSL-Rport Weight Backup Status SVC-IP
  1     extms_prcs1     172.18.8.52                 1             enable
  2     extms_prcs2     172.18.8.53                 1             enable
  3     external_relay1 172.18.8.19                 1             enable
  4     external_relay2 172.18.8.20                 1             enable
  5                     3.3.3.3                     1             enable
  6                     3.3.3.4                     1             enable
================================================================================
```

# 설명
※ show real: LB에 등록된 Real Server 상태를 조회하는 명령
- RIP: Real Server IP
- Status: LB 서비스 활성 상태(enable/disable) 의미
- Weight: 부하분산 가중치
- Backup: Backup Server 여부
- Name: Real Server 이름, - 인 경우 이름(alias)이 미설정된 상태를 의미

# 임계치


# 판단기준
- **양호**: 모든 Real Server의 Status 값이 'enable'인 상태
- **경고**: 'disable' 상태의 Real Server가 존재하는 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

