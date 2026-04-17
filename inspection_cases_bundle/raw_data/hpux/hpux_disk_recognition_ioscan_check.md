# 영역
DISK

# 세부 점검항목
Disk 인식여부 점검

# 점검 내용
디스크 장치의 OS 인식 정상 여부를 점검한다.

# 구분
권고

# 명령어
```bash
ioscan -fnC disk
```

# 출력 결과
```text
Class     I  H/W Path        Driver   S/W State   H/W Type     Description
=========================================================================
disk      0  0/1/1/0.0.0     sdisk    CLAIMED     DEVICE       HP LOGICAL VOLUME
          /dev/dsk/c0t0d0    /dev/rdsk/c0t0d0
disk      1  0/1/1/0.1.0     sdisk    CLAIMED     DEVICE       HP LOGICAL VOLUME
          /dev/dsk/c1t0d0    /dev/rdsk/c1t0d0
```

# 설명
- `ioscan -fnC disk` 명령으로 OS가 인식한 디스크 장치와 디바이스 파일을 확인한다.
- 운영에 필요한 디스크가 `CLAIMED` 상태로 표시되고 `/dev/dsk`, `/dev/rdsk` 경로가 생성되어 있으면 정상으로 본다.
- `UNCLAIMED`, `NO_HW`, `ERROR` 상태나 기대 디스크 누락은 디스크, HBA, SAN, 스토리지 매핑 문제 가능성이 있다.
- 신규 디스크 추가 후에는 필요 시 `insf -e` 실행 여부와 장치 파일 생성을 확인한다.

# 임계치
expected_disk_count
allowed_disk_states

# 판단기준
- **양호**: 필수 디스크가 모두 `CLAIMED` 상태로 인식되는 경우
- **경고**: 필수 디스크 누락 또는 `UNCLAIMED`, `NO_HW`, `ERROR` 상태가 있는 경우
- **확인 필요**: 기대 디스크 목록이 없거나 스토리지 구성 정보가 불명확한 경우
