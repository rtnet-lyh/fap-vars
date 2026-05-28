# 영역
물리 점검

# 세부 점검항목
디스크 상태 점검

# 점검 내용
디스크 Fault 상태 점검

# 구분
필수

# 명령어
```bash
/opt/MegaRAID/storcli/storcli64 /c0 /eall /sall show
```

# 출력 결과
```text

tggitsbackup:/home/maintenance # /opt/MegaRAID/storcli/storcli64 /c0 /eall /sall show
CLI Version = 007.1704.0000.0000 Jan 16, 2021
Operating system = Linux 4.18.0-372.105.1.el8_6.x86_64
Controller = 0
Status = Success
Description = Show Drive Information Succeeded.


Drive Information :
=================

------------------------------------------------------------------------------
EID:Slt DID State DG       Size Intf Med SED PI SeSz Model            Sp Type
------------------------------------------------------------------------------
252:0    11 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:1    10 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:2    16 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:3    12 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:4    15 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:5    14 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:6     8 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:7    13 DHS    0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     D  -
------------------------------------------------------------------------------

EID=Enclosure Device ID|Slt=Slot No|DID=Device ID|DG=DriveGroup
DHS=Dedicated Hot Spare|UGood=Unconfigured Good|GHS=Global Hotspare
UBad=Unconfigured Bad|Sntze=Sanitize|Onln=Online|Offln=Offline|Intf=Interface
Med=Media Type|SED=Self Encryptive Drive|PI=Protection Info
SeSz=Sector Size|Sp=Spun|U=Up|D=Down|T=Transition|F=Foreign
UGUnsp=UGood Unsupported|UGShld=UGood shielded|HSPShld=Hotspare shielded
CFShld=Configured shielded|Cpybck=CopyBack|CBShld=Copyback Shielded
UBUnsp=UBad Unsupported|Rbld=Rebuild

```
# 설명
- 명령어: RAID 컨트롤러에 연결된 전체 물리 디스크 상태를 확인하는 명령어.
- '/c0' 옵션은 0번 RAID 컨트롤러를 의미함.

[참고]
- AI: 'State' 컬럼 설명
Onln: 온라인 상태(양호)
DHS: 대기상태(양호)
offln, failed, UBad: 장애 또는 비정상(경고)


# 임계치
disk_state_value
- State 컬럼의 정상 값

# 판단기준
- **양호**: 각 라인마다 State 값이 `disk_state_value`인 경우.
- **경고**: 각 라인마다 State 값이 `disk_state_value`이 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.