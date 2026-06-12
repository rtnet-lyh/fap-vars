# 영역
CLUSTER

# 세부 점검항목
공유 볼륨 상태 점검

# 점검 내용
공유 볼륨이 지정된 mount point에 정상 마운트되었는지와 Read/Write 상태가 기대값과 일치하는지를 `mount | grep <mount_point>`로 점검합니다.

# 구분
필수

# 명령어
```bash
mount | grep <mount_point>
```

# 출력 결과
```text
/dev/dsk/c0t0d0s0 on / type ufs (rw, logging)
/dev/dsk/shared_vol on /mnt/shared type ufs (rw, logging)
```

# 설명
- `rw`면 읽기/쓰기 가능 상태, `ro`면 읽기 전용 상태입니다.
- 공유 볼륨이 정상 마운트되었는지와 파일시스템 유형을 함께 확인합니다.
- `grep` 결과가 없으면 해당 mount point에 공유 볼륨이 마운트되지 않은 것으로 판단합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found`, `command not found` 같은 실행 오류 문구도 실패로 처리합니다.

# 임계치
- `mount_point`: `/mnt/shared`
- `expected_access_mode`: `rw`
- `expected_filesystem_types`: `ufs`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found,no such file`

# 판단기준
- **정상**: 지정한 `mount_point`가 mount 출력에 존재하고 접근 상태가 `rw`이며 파일시스템 유형도 기준과 일치하는 경우
- **실패**: 공유 볼륨이 마운트되지 않았거나 접근 상태가 `ro` 또는 미확인인 경우
- **실패**: 파일시스템 유형이 기준과 다르거나 출력 파싱에 실패한 경우
- **실패**: `mount | grep <mount_point>` 명령 실행 실패, 실행 오류 문구 확인, `stderr` 출력 확인 시
