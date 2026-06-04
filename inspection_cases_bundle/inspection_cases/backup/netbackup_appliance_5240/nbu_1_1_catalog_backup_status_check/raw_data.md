# 영역
로그

# 세부 점검항목
수행 결과 점검

# 점검 내용
카탈로그 백업 상태 점검

# 구분
필수

# 명령어
```bash
bpdbjobs | awk 'NR==1 || $2=="Catalog"'
```

# 출력 결과
```text
netbackup:/home/maintenance # bpdbjobs | awk 'NR==1 || $2=="Catalog"'
 JobID            Type      State Statu                    Policy   Schedule          Client         Started           Ended    Elapsed       Kilobytes KB Per Sec               Dest StUnit
359517  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/26/2026 12:00:37 05/26/2026 12:02:28  000:01:51         2237536      21669                      MSDP
359516  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/26/2026 12:00:12 05/26/2026 12:00:24  000:00:12          375168     468960                      MSDP
359515  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/26/2026 12:00:03 05/26/2026 12:00:36  000:00:33
359514  Catalog Backup       Done     0                      CATALOG          -        netbackup 05/26/2026 12:00:00 05/26/2026 12:02:28  000:02:28
359256  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/25/2026 12:00:34 05/25/2026 12:02:10  000:01:36         2242016      25445                      MSDP
359255  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/25/2026 12:00:09 05/25/2026 12:00:22  000:00:13          375168     248291                      MSDP
359254  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/25/2026 12:00:04 05/25/2026 12:00:33  000:00:29
359253  Catalog Backup       Done     0                      CATALOG          -        netbackup 05/25/2026 12:00:00 05/25/2026 12:02:10  000:02:10
358996  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/24/2026 12:00:41 05/24/2026 12:02:04  000:01:23         2287904      30443                      MSDP
358995  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/24/2026 12:00:15 05/24/2026 12:00:30  000:00:15          375168     326801                      MSDP


```

# 설명
- 명령어: NetBackup 작업이력 및 작업 상태를 확인하는 명령어.
- awk 'NR==1 || $2=="Catalog"' 옵션은 헤더라인과 Type이 Catalog Backup인 작업을 필터링 하기위해 사용함.
- State: Done이면 종료된 상태. Active면 수행 중 상태.
- Statu: 작업결과 코드, 0이면 정상완료 나머지 값은 실패 및 오류

[참고]
- Catalog Backup: Netbackup 구성, 정책정보, 이미지 카탈로그 등 백업 복구에 필요한 핵심 메타 데이터를 보고하기 위한 백업 작업.

# 임계치


# 판단기준
- **양호**: 각 라인마다 State 값이 Done이고 Statu 값이 0인 상태.
- **경고**: 각 라인마다 State 값이 Done이 아니거나 Statu 값이 0이 아닌 상태.
- **확인 필요**: 명령어 실패 및 파싱 불가.