# 영역
로그

# 세부 점검항목
DISK 오류 블록 로그

# 점검 내용
Disk 장치의 오류 점검 (Disk fail)

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
- 스토리지 전체 Disk 운영 상태를 확인하는 명ㄹ영어
- Disk 사용 상태(In Use/Spare) 및 Storage 운영 상태를 점검 가능
- Disk 장애(Fail/Offline/Degraded) 발생 여부를 확인하여 저장장치 이상 여부를 점검함
- Normal - Storage operational: 스토리지 정상 운영 상태
- In Use: 현재 사용 중인 Disk
- Spare: 장애 대비 대기 Disk 

# 임계치


# 판단기준
- **양호**: Storage 상태가 "Normal - Storage operational"이며, Disk 장애 관련 메시지가 없는 상태 
- **경고**: Storage 상태가 "Normal - Storage operational"이 아니거나, failed/error/offline/degraded 상태 존재
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
