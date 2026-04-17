# 영역
OS

# 세부 점검항목
Path 이중화 점검

# 점검 내용
스토리지 디스크 경로 이중화 정상 여부를 점검한다.

# 구분
권고

# 명령어
```bash
ioscan -m dsf
scsimgr get_info -D <ioscan에서 확인한 persistent_dsf>
```

# 출력 결과
```text
Persistent DSF           Legacy DSF(s)
========================================
/dev/rdisk/disk1         /dev/rdsk/c2t0d0
                         /dev/rdsk/c3t0d0

STATUS INFORMATION FOR LUN : /dev/rdisk/disk1
Generic Status: OPTIMAL
Number of Paths: 2
```

# 설명
- `ioscan -m dsf`로 persistent DSF와 legacy DSF 매핑을 확인하고, 동일 LUN에 여러 경로가 있는지 확인한다.
- `ioscan -m dsf` 출력에서 확인되는 `/dev/rdisk/disk*` persistent DSF를 대상으로 `scsimgr get_info -D <persistent_dsf>`를 순차 실행한다.
- 각 LUN의 `Number of Paths`와 `Generic Status`를 확인하고, `ioscan -m dsf`의 legacy DSF 경로 수도 함께 비교한다.
- 경로 수가 기대보다 적거나 LUN 상태가 `OPTIMAL`이 아니면 SAN 경로 장애, zoning, 스토리지 포트 장애 가능성이 있다.
- HP-UX 버전과 스토리지 구성에 따라 `scsimgr` 지원 여부와 출력 형식이 다를 수 있다.

# 임계치
expected_path_count
required_lun_status

# 판단기준
- **양호**: 모든 persistent DSF의 legacy DSF 경로 수와 `scsimgr` 경로 수가 기대값 이상이고 상태가 `OPTIMAL`인 경우
- **경고**: 하나 이상의 persistent DSF에서 경로 수 부족, 비정상 경로, LUN 상태 비정상이 확인되는 경우
- **확인 필요**: 경로 이중화 구성 기준이 없거나 명령이 지원되지 않는 경우
