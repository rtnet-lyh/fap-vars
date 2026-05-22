# 영역
파일시스템 사용률

# 세부 점검항목
DB시스템 로그 파일시스템

# 점검 내용
DB 작동중 발생하는 기록에 대한 물리적인 로그 저장 공간 사용률(Full 시 서비스 불가)

# 구분
필수

# 명령어 - oracle_home: 오라클 홈 경로
```bash
df -k {{ oracle_home }}
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ df -k $ORACLE_HOME
Filesystem           1024-blocks        Used   Available Capacity  Mounted on
/dev/vx/dsk/ttips_home01dg/ttips_homevol01
                       104806400    12304871    86732892    13%    /TTIPS_HOME
```

# 설명
- %Use : 파일 시스템의 사용률 확인

# 임계치
max_used_percent: 파일시스템 최대 사용률

# 판단기준
- **양호**: (Used/Total)*100 값이 `max_used_percent`를 초과하지 않는 상태
- **경고**: (Used/Total)*100 값이 `max_used_percent`를 초과한 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

