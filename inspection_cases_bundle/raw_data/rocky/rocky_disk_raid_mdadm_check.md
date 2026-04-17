# 영역
DISK

# 세부 점검항목
Disk 이중화 정상 여부

# 점검 내용
Disk 이중화 정상 유무 점검(레이드 구성 및 State의 상태가 Ok/Maintenance)

# 구분
권고

# 명령어
cat /proc/mdstat; echo "-----"; for md in /dev/md*; do [ -e "$md" ] && mdadm --detail "$md"; done

# 출력 결과
Personalities : [raid1]
md0 : active raid1 sda1[0] sdb1[1]
      104320 blocks [2/2] [UU]

-----
/dev/md0:
           Version : 1.2
        Raid Level : raid1
        Array Size : 104320
     Raid Devices : 2
    Total Devices : 2
      State : clean
 Active Devices : 2
Working Devices : 2
 Failed Devices : 0
  Spare Devices : 0

# 설명
본 항목은 mdadm 기반 소프트웨어 RAID 구성 여부와 상태를 점검한다.
점검 시 /proc/mdstat 및 mdadm --detail 결과를 통해 RAID 레벨, 활성 디스크 수, 실패 디스크 수를 확인한다.
RAID 배열이 active 상태이고 모든 멤버 디스크가 정상이며 failed 장치가 없으면 양호로 판단한다.
배열이 degraded 상태이거나 일부 멤버가 비정상이면 이중화 장애로 판단한다.
md 장치가 존재하지 않으면 mdadm 소프트웨어 RAID가 미구성된 것으로 본다.
하드웨어로 구성되어있을수 있기때문에 이러한 경우, 표기한다.

# 임계치

# 판단기준
RAID 배열이 active 상태이고 mdadm --detail 결과의 State가 clean, active 등 정상 상태이며
Active Devices 수와 Raid Devices 수가 같고 Failed Devices 가 0 이면 양호로 판단한다.

RAID 배열이 degraded 이거나 State가 recover, resync, failed, inactive 등 비정상 상태이거나
Active Devices 수가 Raid Devices 수보다 적거나 Failed Devices 가 1 이상이면 불량으로 판단한다.

/dev/md* 장치가 존재하지 않으면 mdadm 소프트웨어 RAID 미구성으로 판단하며,
하드웨어 RAID 사용 가능성이 있으므로 별도 확인 필요로 표기한다.


