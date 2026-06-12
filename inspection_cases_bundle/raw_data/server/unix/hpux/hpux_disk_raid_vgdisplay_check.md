# 영역
DISK

# 세부 점검항목
Disk 이중화 정상 여부

# 점검 내용
볼륨 그룹과 물리 볼륨 상태를 통해 디스크 이중화 정상 여부를 점검한다.

# 구분
권고

# 명령어
```bash
vgdisplay -v
```

# 출력 결과
```text
--- Volume groups ---
VG Name                     /dev/vg00
VG Status                   available
Max PV                      16
Cur PV                      2
Act PV                      2

--- Physical volumes ---
PV Name                     /dev/dsk/c0t0d0
PV Status                   available
PV Name                     /dev/dsk/c1t0d0
PV Status                   available
```

# 설명
- `vgdisplay -v` 명령으로 HP-UX LVM 볼륨 그룹과 물리 볼륨 상태를 확인한다.
- 운영 디스크가 LVM 미러링 또는 스토리지 이중화 구조로 구성되어 있는지 확인한다.
- `Cur PV`와 `Act PV`가 다르거나 `PV Status`가 `available`이 아니면 디스크 경로 또는 물리 디스크 이상 가능성이 있다.
- 하드웨어 RAID 또는 외장 스토리지 이중화 환경은 별도 관리 도구 결과와 함께 표기한다.

# 임계치
expected_active_pv_count
required_pv_status

# 판단기준
- **양호**: 필요한 물리 볼륨이 모두 `available`이고 활성 PV 수가 기대값과 일치하는 경우
- **경고**: PV 누락, 비활성 PV, 미러 장애, 활성 PV 수 불일치가 있는 경우
- **확인 필요**: 하드웨어 RAID 등 OS 명령만으로 이중화 상태 판단이 어려운 경우
