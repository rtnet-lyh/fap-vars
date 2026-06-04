# 영역
사용량 점검

# 세부 점검항목
SW 상태 점검

# 점검 내용
백업 Process, 백업 Client 연결 상태 등 점검

# 구분
필수

# 명령어
```bash
bpdbjobs
```

# 출력 결과
```text

atmsbackup:/home/maintenance # bpdbjobs
 JobID            Type      State Statu                    Policy   Schedule          Client         Started           Ended    Elapsed       Kilobytes KB Per Sec               Dest StUnit
 57181    Image Delete       Done     0                                                      05/26/2026 16:39:45 05/26/2026 16:39:51  000:00:06
 57180          Backup       Done     0              VM_TIPS_WAS1       full       tips_was1 05/26/2026 15:30:16 05/26/2026 16:39:37  001:09:21       129830560      31534                      MSDP
 57179        Snapshot       Done     0              VM_TIPS_WAS1          -       tips_was1 05/26/2026 15:30:00 05/26/2026 16:39:45  001:09:45                                                 MSDP
 57178    Image Delete       Done     0                                                      05/26/2026 14:15:19 05/26/2026 14:15:28  000:00:09
 57177          Backup       Done     0              VM_TIPS_WAS2       full       tips_was2 05/26/2026 13:30:17 05/26/2026 14:15:11  000:44:54        86671552      32458                      MSDP
 57176        Snapshot       Done     0              VM_TIPS_WAS2          -       tips_was2 05/26/2026 13:30:00 05/26/2026 14:15:19  000:45:19                                                 MSDP
 57175  Catalog Backup       Done     0                   CATALOG       full      atmsbackup 05/26/2026 12:00:36 05/26/2026 12:05:07  000:04:31        10674208      40994                      MSDP
 57174  Catalog Backup       Done     0                   CATALOG       full      atmsbackup 05/26/2026 12:00:11 05/26/2026 12:00:27  000:00:16          238528     140724                      MSDP
 57173  Catalog Backup       Done     0                   CATALOG       full      atmsbackup 05/26/2026 12:00:04 05/26/2026 12:00:35  000:00:31
 57172  Catalog Backup       Done     0                   CATALOG          -      atmsbackup 05/26/2026 12:00:00 05/26/2026 12:05:11  000:05:11
 57171    Image Delete       Done     0                                                      05/26/2026 11:00:27 05/26/2026 11:00:38  000:00:11
 57170          Backup       Done     0 VRTS_NBA_Dedupe_Catalog_atmsbackup       Full      atmsbackup 05/26/2026 11:00:00 05/26/2026 11:00:25  000:00:25          113888      10163                      MSDP

```
# 설명
- 명령어: RAID 컨트롤러에 연결된 전체 물리 디스크 상태를 확인하는 명령어.

[참고]
- 다른 값에 스페이스 들어간 값이 많아 파싱 시 고정 컬럼위치만으로 판단하지 않도록 주의 필요.


# 임계치


# 판단기준
- **양호**: 'State' 컬럼 값이 Done이며 'Statu' 값이 0인 상태.
- **경고**: 'State' 값이 Done이 아니거나 'Statu' 값이 0이 아닌 상태.
- **확인 필요**: 명령어 실패 및 파싱 불가.