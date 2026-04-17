# 영역
OS

# 세부 점검항목
HBA 연결상태 점검

# 점검 내용
HBA 연결 정상 유무를 점검한다.

# 구분
권고

# 명령어
```bash
ioscan -fnC fc
```

# 출력 결과
```text
Class     I  H/W Path        Driver      S/W State   H/W Type     Description
===========================================================================
fc        0  0/2/1/0         fcd         CLAIMED     INTERFACE    HP Fibre Channel Mass Storage Adapter
fc        1  0/2/1/1         fcd         CLAIMED     INTERFACE    HP Fibre Channel Mass Storage Adapter
```

# 설명
- `ioscan -fnC fc` 명령으로 Fibre Channel HBA가 OS에서 정상 인식되는지 확인한다.
- HBA 상태가 `CLAIMED`이면 드라이버가 장치를 정상 제어하는 상태로 본다.
- `UNCLAIMED`, `NO_HW`, `ERROR` 상태는 HBA, 드라이버, 슬롯, 펌웨어 문제 가능성이 있다.
- 실제 SAN 연결 상태와 속도는 스토리지 관리 도구, 스위치 포트, HBA 상세 명령으로 추가 확인한다.

# 임계치
expected_hba_count
allowed_hba_states

# 판단기준
- **양호**: 운영 대상 HBA가 모두 `CLAIMED` 상태로 확인되는 경우
- **경고**: HBA 누락 또는 `UNCLAIMED`, `NO_HW`, `ERROR` 상태가 있는 경우
- **확인 필요**: HBA 미구성 서버이거나 기대 HBA 수 기준이 없는 경우
