# 영역
DISK

# 세부 점검 항목
클러스터 공유 볼륨 마운트 상태

# 점검 내용
지정한 공유 볼륨 경로가 실제로 마운트되어 있는지, 읽기/쓰기 모드와 볼륨 상태가 정상인지 확인합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $p='C:\\mnt\\shared\\'; $pt=Get-Partition | Where-Object { $_.AccessPaths -contains $p -or $_.AccessPaths -contains $p.TrimEnd('\\') }; if($pt){ $v=$pt | Get-Volume; [pscustomobject]@{Device=\"Disk$($pt.DiskNumber)\\Partition$($pt.PartitionNumber)\"; MountedOn=$p.TrimEnd('\\'); FileSystem=$v.FileSystem; Mode=$(if($pt.IsReadOnly){'ro'}else{'rw'}); Status=$pt.OperationalStatus; Health=$v.HealthStatus} | Format-List } else { \"Mount point not found: $p\" }
```

# 출력 결과
```text
Device     : Disk1\\Partition2
MountedOn  : C:\mnt\shared
FileSystem : NTFS
Mode       : rw
Status     : Online
Health     : Healthy
```

# 설명
- 기본 경로는 `C:\mnt\shared\`이며 파티션과 볼륨 정보를 함께 확인합니다.
- 마운트 경로, 모드, OperationalStatus, HealthStatus를 모두 만족해야 정상으로 판단합니다.

# 임계치
- `expected_mount_path`: `C:\mnt\shared\`
- `expected_mode`: `rw`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 기대한 경로에 볼륨이 연결되어 있고 모드가 `rw`이며 상태와 헬스가 정상입니다.
- **경고**: 마운트 지점을 찾지 못했거나 경로, 모드, 상태 값이 기대와 다릅니다.


