# 영역
CLUSTER

# 세부 점검항목
공유 볼륨 상태 점검

# 점검 내용
공유 볼륨 Read/Write 상태 및 마운트 정상 유무 점검(File System State On, HSM Server Not Responding)

# 구분
권고

# 명령어
```bash
findmnt <마운트경로>
```

# 출력 결과
```text
TARGET         SOURCE FSTYPE OPTIONS
/run/user/1000 tmpfs  tmpfs  rw,nosuid,nodev,relatime,seclabel,size=1572692k,nr_inodes=393173,mode=700,uid=1000,gid=1000,inode64
```

# 설명
- 본 항목은 클러스터 공유 볼륨이 지정된 마운트 경로에 정상 마운트되어 있고, 파일시스템이 읽기/쓰기 가능한 `rw` 옵션으로 동작하는지 확인한다.
- `findmnt <마운트경로>` 결과가 출력되면 해당 경로에 파일시스템이 마운트된 상태로 본다. 출력이 없으면 공유 볼륨이 마운트되지 않았거나 마운트 경로 임계치가 실제 경로와 다를 수 있으므로 클러스터 리소스 상태와 `/etc/fstab`, systemd mount unit, 스토리지 경로를 함께 확인한다.
- `findmnt` 출력의 `OPTIONS` 컬럼에 `rw`가 포함되어 있으면 읽기/쓰기 상태로 판단한다. `ro`가 포함되어 있으면 파일시스템 오류, 스토리지 경로 장애, 클러스터 보호 동작 등으로 읽기 전용 전환된 상태일 수 있으므로 즉시 원인 확인이 필요하다.
- `File System State On` 상태는 공유 파일시스템이 클러스터 리소스 관점에서 활성 상태임을 의미한다. 반대로 `HSM Server Not Responding` 같은 응답 불가 메시지가 함께 확인되면 공유 볼륨 접근성, 클러스터 서비스, 스토리지 연결 상태를 점검한다.
- 여러 공유 볼륨을 점검할 경우 임계치에 마운트 경로를 `|`로 구분하여 등록하고, 각 경로별 `findmnt <마운트경로>` 결과의 존재 여부와 `OPTIONS` 컬럼의 `rw`/`ro` 옵션을 확인한다.

# 임계치
shared_volume_mount_paths: /mnt/shared

# 판단기준
- **성공**: 점검 대상 마운트 경로가 `findmnt` 결과에 존재하고, `OPTIONS` 컬럼에 `rw`가 포함되어 있는 경우
- **실패**: 점검 대상 마운트 경로가 `ro` 옵션으로 마운트되어 있는 경우
- **실패**: 점검 대상 마운트 경로가 `mount` 결과에 없거나, 출력은 있으나 `rw`/`ro` 옵션을 판별할 수 없는 경우
- **참고**: `shared_volume_mount_paths`는 기본값 `/mnt/shared`를 사용하며, 여러 경로는 `/mnt/shared|/mnt/share2`처럼 `|`로 구분한다.
