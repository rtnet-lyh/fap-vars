# 영역
물리 점검

# 세부 점검항목
장비 Tape 관리 장치 인식 점검

# 점검 내용
드라이브, 라이브러리 인식 상태 점검

# 구분
필수

# 명령어
```bash
tpconfig -l
```

# 출력 결과(결과있음 - 172.18.8.28)
```text

netbackup:/home/maintenance # tpconfig -l
Device Robot Drive       Robot                    Drive                 Device                                                              Second
Type     Num Index  Type DrNum Status  Comment    Name                  Path                                                                Device Path
robot      0    -    TLD    -       -  -          -                     /dev/tape/by-path/pci-0000:87:00
  drive    -    0 hcart3    1    DOWN  -          HP.ULTRIUM6-SCSI.000  /dev/tape/by-path/pci-0000:87:00.1-fc-0x50014380272cdeee-lun-0-nst
  drive    -    1 hcart3    2    DOWN  -          HP.ULTRIUM6-SCSI.001  /dev/tape/by-path/pci-0000:87:00.0-fc-0x50014380272cdef1-lun-0-nst

```
# 출력 결과(결과없음 - 172.18.8.27,30)
```text

tggitsbackup:/home/maintenance # tpconfig -l
Device Robot Drive       Robot                    Drive  Device  Second
Type     Num Index  Type DrNum Status  Comment    Name  Path  Device Path

```
# 설명
- 명령어: NetBackup에서 구성된 Tape, Drive, Device 정보를 확인하는 명령어. 
- 출력 결과에 'robot' 항목 존재 시 tape이 구성되어있다고 판단.
- Tape 미 사용 장비(출력 결과: 결과없음)에는 '해당 없음','양호' 처리가 옳아보임.

[참고]
- 'Device Path'가 긴 경우 터미널 화면에서 줄바꿈이 발생되어 정렬이 깨질 수 있으므로 파싱 시 고정 컬럼위치만으로 판단하지 않도록 주의 필요.
- AI: 'Status'에 나올 수 있는 값이 'UP', 'DOWN', 'DISABLED', '-'라고 함.

# 임계치
status_value
- status 컬럼의 정상 값

# 판단기준
- **양호**: 'robot' 값이 존재하지 않거나,'robot' 값이 존재하면서 'status' 값이 `status_value`인 경우.
- **경고**: 'robot' 값이 존재하고, 'status' 값이 `status_value`가 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.