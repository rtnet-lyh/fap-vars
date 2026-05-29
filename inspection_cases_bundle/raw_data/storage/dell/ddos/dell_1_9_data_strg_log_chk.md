# 영역
로그

# 세부 점검항목
데이터 스토리지 디스크

# 점검 내용
스토리지 디스크 Fault 여부

# 구분
필수

# 명령어
```bash
disk status
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
sysadmin@localhost# disk status
Normal - Storage operational

Disk States   Active tier   Cache tier
-----------   -----------   ----------
In Use        25            2
Spare         2             -
TOTAL DISKS   27            2
-----------   -----------   ----------

```

# 설명
- disk status 명령어를 통해 스토리지 디스크 운영 상태 및 장애 여부를 확인할 수 있음
- Storage operational 상태를 통해 스토리지 정상 동작 여부를 점검 가능하며, 디스크 장애 (Fail) 및 스토리지 비정상 상태 여부를 확인할 수 있음

# 임계치
valid_disk_status = "Normal - Storage operational"


# 판단기준
- **양호**: 출력 결과가 `valid_disk_status`와 일치할 경우
- **경고**: 출력 결과가 `valid_disk_status`와 일치하지 않을 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
