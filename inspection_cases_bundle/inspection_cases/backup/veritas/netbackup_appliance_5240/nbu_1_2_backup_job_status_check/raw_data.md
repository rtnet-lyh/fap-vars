# 영역
로그

# 세부 점검항목
수행 결과 점검

# 점검 내용
백업SW 로그 점검

# 구분
필수

# 명령어
```bash
bpdbjobs | awk 'NR==1 || $2=="Backup"'
```

# 출력 결과
```text
tggitsbackup:/home/maintenance # bpdbjobs | awk 'NR==1 || $2=="Backup"'
 JobID            Type      State Statu                    Policy   Schedule          Client         Started           Ended    Elapsed       Kilobytes KB Per Sec               Dest StUnit
 37320          Backup       Done     0              SDPOL-oracle       ARCH  polestar_TC-bk 05/26/2026 02:33:12 05/26/2026 02:34:29  000:01:17         7930720     114745     stu_disk_tggitsbackup
 37318          Backup       Done     0              SDPOL-oracle       DATA  polestar_TC-bk 05/26/2026 02:00:15 05/26/2026 02:33:12  000:32:57       225567840     114955     stu_disk_tggitsbackup
 37317          Backup       Done     0              SDPOL-oracle      start  polestar_TC-bk 05/26/2026 02:00:00 05/26/2026 02:05:17  000:05:17           14112         46     stu_disk_tggitsbackup
 37316          Backup       Done     0            polestar_TC-FS       Incr  polestar_TC-bk 05/26/2026 00:00:00 05/26/2026 00:05:49  000:05:49        38645216     113596     stu_disk_tggitsbackup
 37269          Backup       Done     0        polestar_TC-oracle       ARCH  polestar_TC-bk 05/25/2026 02:24:01 05/25/2026 02:26:57  000:02:56        19349792     114845     stu_disk_tggitsbackup
 37267          Backup       Done     0        polestar_TC-oracle       DATA  polestar_TC-bk 05/25/2026 02:00:15 05/25/2026 02:24:01  000:23:46       162479200     114958     stu_disk_tggitsbackup
 37266          Backup       Done     0        polestar_TC-oracle      start  polestar_TC-bk 05/25/2026 02:00:00 05/25/2026 02:05:19  000:05:19           13952         46     stu_disk_tggitsbackup
 37262          Backup       Done     0            polestar_TC-FS       Incr  polestar_TC-bk 05/25/2026 00:00:00 05/25/2026 00:05:49  000:05:49        38598880     113643     stu_disk_tggitsbackup
 37216          Backup       Done     0            polestar_TC-FS       Full  polestar_TC-bk 05/24/2026 00:00:00 05/24/2026 00:18:19  000:18:19       121952800     114345     stu_disk_tggitsbackup


```

# 설명
- 명령어: NetBackup 작업이력 및 작업 상태를 확인하는 명령어.
- awk 'NR==1 || $2=="Backup"' 옵션은 헤더라인과 Backup 문자열인 작업을 필터링 하기위해 사용함.
- State: Done이면 종료된 상태. Active면 수행 중 상태.
- Statu: 작업결과 코드, 0이면 정상완료 나머지 값은 실패 및 오류

# 임계치


# 판단기준
- **양호**: 각 라인마다 State 값이 Done이고 Statu 값이 0인 상태.
- **경고**: 각 라인마다 State 값이 Done이 아니거나 Statu 값이 0이 아닌 상태.
- **확인 필요**: 명령어 실패 및 파싱 불가.