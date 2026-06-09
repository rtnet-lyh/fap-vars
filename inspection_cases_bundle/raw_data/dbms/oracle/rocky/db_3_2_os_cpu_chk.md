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
ps -eo pid,comm,%cpu --sort=-%cpu | grep ora_ | grep -v grep | head -10
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/home/oracle> ps -eo pid,comm,%cpu --sort=-%cpu | grep ora_ | grep -v grep | head -10
3229820 ora_vkrm_unidev  0.1
3229828 ora_dia0_unidev  0.1
 139563 ora_w002_unidev  0.0
 359607 ora_m004_unidev  0.0
 475615 ora_w005_unidev  0.0
 524302 ora_w009_unidev  0.0
 652248 ora_w004_unidev  0.0
 708294 ora_w001_unidev  0.0
 728381 ora_w00e_unidev  0.0
 811760 ora_m006_unidev  0.0




---
```

# 설명
- `ps` 명령을 통해 Oracle 관련 메인 프로세스, 메모리, CPU 사용률을 점검합니다.

# 임계치
max_usage_percent: 최대 허용 자원(CPU/메모리) 사용률

# 판단기준
- **양호**: 프로세스 상태가 정상이고 자원 사용률이 임계치 이하로 유지됨
- **경고**: 자원 사용률이 임계치를 초과하거나 비정상 상태, 프로세스가 구동되지 않음
- **확인 필요**: 명령어 오류 또는 수집 결과 포맷 불일치로 확인 불가
