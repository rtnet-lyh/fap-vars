# 영역
CLUSTER

# 세부 점검항목
공유 볼륨 상태 점검

# 점검 내용
Serviceguard 패키지에서 사용하는 공유 볼륨과 파일시스템의 마운트 정상 여부를 점검한다.

# 구분
권고

# 명령어
```bash
mount
```

# 출력 결과
```text
/dev/vgshared/lvol1 on /app type vxfs rw,suid,delaylog,largefiles,dev=4000001 on Thu Dec 30 12:10:01 2025
/dev/vgshared/lvol2 on /data type vxfs rw,suid,delaylog,largefiles,dev=4000002 on Thu Dec 30 12:10:01 2025
```

# 설명
- `mount` 명령으로 공유 볼륨 파일시스템이 기대한 마운트 지점에 읽기/쓰기 가능 상태로 마운트되어 있는지 확인한다.
- Serviceguard 패키지에서 사용하는 공유 볼륨은 패키지 실행 노드에서만 활성화되어야 한다.
- 필수 공유 볼륨이 누락되었거나 읽기 전용으로 마운트되면 서비스 장애 또는 데이터 접근 장애가 발생할 수 있다.
- 환경에 따라 `bdf`, `vgdisplay -v`, 패키지 구성 파일을 함께 확인한다.

# 임계치
required_shared_mounts
required_mount_options

# 판단기준
- **양호**: 필수 공유 파일시스템이 기대 마운트 지점에 `rw` 상태로 마운트된 경우
- **경고**: 필수 공유 파일시스템이 누락되었거나 `ro` 상태인 경우
- **확인 필요**: 공유 볼륨 구성 정보가 없거나 Serviceguard 미구성 서버인 경우
