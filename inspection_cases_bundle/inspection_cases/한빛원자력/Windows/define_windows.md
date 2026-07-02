# Windows 서버 시스템 점검 항목 명세서

## 01. CPU 점검
* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: CPU 점검
* **명령어**: 
  ```powershell
  powershell.exe -NoProfile -Command "$paths = @('\Processor(_Total)\% User Time', '\Processor(_Total)\% Privileged Time','\Processor(_Total)\% Idle Time', '\Processor(_Total)\% Interrupt Time'); $data = Get-Counter -Counter $paths -SampleInterval 1 -MaxSamples 3; $data.CounterSamples | Group-Object Path | ForEach-Object { $avg = ($_.Group | Measure-Object -Property CookedValue -Average).Average; $counter = [regex]::Match($_.Name, '% .*time$', 'IgnoreCase').Value.ToLower(); switch ($counter) { '% user time' { $name = 'User' } '% privileged time' { $name = 'Privileged' } '% idle time' { $name = 'Idle' } '% interrupt time' { $name = 'Interrupt' } default { $name = $_.Name } }; '{0}={1:N2}' -f $name, $avg }"

```

* **정상 기준**: User 및 Privileged Time 합산 사용률이 80% 이하이고, Idle 상태가 20% 이상이며, Interrupt(IRQ) 비율이 5% 이하일 것
* **threshold key**:
* `max_user_sys_pct`: 80
* `min_idle_pct`: 20
* `max_irq_pct`: 5



---

## 02. CPU 코어별 상태 점검

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: CPU 코어별 상태 점검
* **명령어**: `wmic path Win32_Processor get DeviceID,Status,Availability,CpuStatus,NumberOfCores,NumberOfLogicalProcessors /value`
* **정상 기준**: 각 코어의 Status가 OK이고, Availability 값이 3(Running/Full Power)이며, CpuStatus가 1(OK)일 것
* **threshold key**:
* `status_ok`: "OK"
* `availability_ok`: 3
* `cpu_status_ok`: 1



---

## 03. Memory 사용률

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: Memory 사용률
* **명령어**: `wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value`
* **정상 기준**: 물리 메모리 사용률이 80% 이하이며, 여유 메모리 비율이 20% 이상일 것
* **threshold key**:
* `max_used_mem`: 80
* `min_free_mem_pct`: 20



---

## 04. Memory 상태 확인

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: Memory 상태 확인
* **명령어**: `wmic memorychip get BankLabel,Capacity,ConfiguredClockSpeed,Speed,Status /value`
* **정상 기준**: 장착된 메모리 칩의 하드웨어 상태 및 응답 정보 수집 (임계값 없음)

---

## 05. Paging Space

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: Paging Space
* **명령어**: `wmic pagefile get AllocatedBaseSize,CurrentUsage,PeakUsage /value`
* **정상 기준**: 페이징 파일(가상 메모리)의 사용률이 50% 이하일 것
* **threshold key**:
* `max_used_swap`: 50



---

## 06. 파일시스템 사용량

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: 파일시스템 사용량
* **명령어**: `wmic LogicalDisk where "DriveType=3" get DeviceID,Size,FreeSpace /value`
* **정상 기준**: 모든 로컬 디스크(DriveType=3)의 디스크 공간 사용률이 80% 이하일 것
* **threshold key**: `inspection_criteria`: 80

---

## 07. Disk Swap 사용률

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: Disk Swap 사용률
* **명령어**: `wmic pagefile get Name,AllocatedBaseSize,CurrentUsage,PeakUsage /value`
* **정상 기준**: 디스크 스왑 파일별 사용률이 50% 이하일 것
* **threshold key**:
* `max_used_swap`: 50



---

## 08. DISK 이중화 정상 여부

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: DISK 이중화 정상 여부
* **명령어**:
```powershell
powershell.exe -NoProfile -Command "$cmd = Get-Command Get-VirtualDisk -ErrorAction SilentlyContinue; if (-not $cmd) { 'NOT_APPLICABLE=Get-VirtualDisk unavailable'; exit 0 }; try { $vds = Get-VirtualDisk -ErrorAction Stop } catch { 'Access is denied'; exit 0 }; if (-not $vds) { 'NOT_APPLICABLE=No virtual disk'; exit 0 }; foreach ($vd in $vds) { 'Name=' + $vd.FriendlyName; 'Resiliency=' + $vd.ResiliencySettingName; 'HealthStatus=' + $vd.HealthStatus; 'OperationalStatus=' + (($vd.OperationalStatus -join ',')); '' }"

```


* **정상 기준**: 저장소 공간(Storage Spaces)의 가상 디스크 이중화 및 헬스 상태 수집 (임계값 미지정)

---

## 09. DISK 인식 여부 점검

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: DISK 인식 여부 점검
* **명령어**: `powershell -Command "Get-Disk | Select-Object Number, FriendlyName, Size, OperationalStatus, HealthStatus, BusType, PartitionStyle | ForEach-Object { 'Number=' + $_.Number; 'FriendlyName=' + $_.FriendlyName; 'Size=' + $_.Size; 'OperationalStatus=' + $_.OperationalStatus; 'HealthStatus=' + $_.HealthStatus; 'BusType=' + $_.BusType; 'PartitionStyle=' + $_.PartitionStyle; '' }"`
* **정상 기준**: 연결된 물리 디스크 상태 중 'Offline' 또는 'Failed' 상태인 디스크가 없을 것
* **threshold key**: `inspection_criteria`: "Offline,Failed"

---

## 10. DISK I/O 점검

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: DISK I/O 점검
* **명령어**: `powershell -Command "$p = (Get-Counter -ListSet 'PhysicalDisk').Paths | Where-Object { $_ -like '*Avg. Disk sec/Read' -or $_ -like '*Avg. Disk sec/Write' }; Get-Counter -Counter $p -SampleInterval 1 -MaxSamples 1 | Select-Object -ExpandProperty CounterSamples | Where-Object { $_.Path -like '*(_total)*' } | Select-Object @{Name='Metric'; Expression={if($_.Path -like '*read*') {'Read Latency'} else {'Write Latency'}}}, @{Name='Latency(ms)'; Expression={[Math]::Round($_.CookedValue * 1000, 3)}}"`
* **정상 기준**: 디스크의 평균 읽기/쓰기 지연 시간(Latency)이 20ms 이하일 것
* **threshold key**: `inspection_criteria`: 20

---

## 11. DISK I-Node 정상여부

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: DISK I-Node 정상여부
* **명령어**: `powershell -Command "Get-Volume | Where-Object DriveLetter | ForEach-Object { fsutil dirty query ($_.DriveLetter + ':') }"`
* **정상 기준**: 파일시스템의 Dirty 비트 상태를 점검하여 "is Dirty"(손상/오류 가능성) 상태가 아닐 것
* **threshold key**: `inspection_criteria`: "is Dirty"

---

## 12. Kernel parameter Check

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: Kernel parameter Check
* **명령어**: `powershell -Command "netsh int tcp show global; netsh int ip show global; Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters'"`
* **정상 기준**: 네트워크 및 TCP/IP 시스템 전역 커널 파라미터 구성 정보 수집 (임계값 없음)

---

## 13. 로그 점검

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: 로그 점검
* **명령어**: `powershell -Command "Get-EventLog -LogName System -Newest 50 | ForEach-Object { '{0} [{1}] ({2}) {3}' -f $_.TimeGenerated, $_.EntryType, $_.Source, $_.Message.Replace(\"`n",' ').Trim().Substring(0, [Math]::Min($_.Message.Length, 80)) }"`
* **정상 기준**: 최근 50개의 시스템 이벤트 로그 중 'Error' 또는 'Warning' 유형의 이벤트 로그가 나오지 않거나 최소화되어 있을 것
* **threshold key**: `inspection_criteria`: "Error,Warning"

---

## 14. Cluster 데몬 상태

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: Cluster 데몬 상태
* **명령어**: `powershell -Command "try { Get-Service clussvc -ErrorAction Stop | Out-Null; Write-Host '[Node Status]'; Get-ClusterNode | ForEach-Object { '{0} : {1}' -f $_.Name, $_.State }; Write-Host '---'; Write-Host '[Service Status]'; Get-ClusterResource | ForEach-Object { '{0} : {1}' -f $_.Name, $_.State } } catch { $_ | Out-String }"`
* **정상 기준**: 명령어 부재 시 정상 통과 처리를 허용하며, 클러스터 노드 및 리소스 상태 중 'Down', 'Paused', 'Offline', 'Failed'가 없을 것
* **threshold key**:
* `ok_if_command_missing`: true
* `errormsg`: "Down,Paused,Offline,Failed"



---

## 15. 공유 볼륨 점검 상태

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: 공유 볼륨 점검 상태
* **명령어**:
```powershell
powershell.exe -NoProfile -Command "$cmd = Get-Command Get-ClusterSharedVolume -ErrorAction SilentlyContinue; if (-not $cmd) { 'NOT_APPLICABLE=Get-ClusterSharedVolume unavailable'; exit 0 }; $csvs = Get-ClusterSharedVolume; if (-not $csvs) { 'NOT_APPLICABLE=No cluster shared volume'; exit 0 }; foreach ($csv in $csvs) { 'Name=' + $csv.Name; 'State=' + $csv.State; 'Path=' + $csv.SharedVolumeInfo.FriendlyVolumeName; '' }"

```


* **정상 기준**: 클러스터 공유 볼륨(CSV)의 이름, 상태 및 연결 경로 정보 수집 (임계값 미지정)

---

## 16. NW 링크 상태

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: NW 링크 상태
* **명령어**: `wmic nic where "PhysicalAdapter=True" get Name,NetConnectionID,NetConnectionStatus,NetEnabled,Speed,AdapterType,PhysicalAdapter /format:list`
* **정상 기준**: 실제 활성화된 물리 네트워크 어댑터(NIC)의 연결 속도가 최소 1Mbps 이상으로 정상 UP 상태일 것
* **threshold key**:
* `min_speed_mbps`: 1



---

## 17. NIC 이중화 상태

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: NIC 이중화 상태
* **명령어**:
```powershell
powershell.exe -NoProfile -Command "$teamCmd = Get-Command Get-NetLbfoTeam -ErrorAction SilentlyContinue; $memberCmd = Get-Command Get-NetLbfoTeamMember -ErrorAction SilentlyContinue; if (-not $teamCmd -or -not $memberCmd) { 'NOT_APPLICABLE=NIC Teaming cmdlets unavailable'; exit 0 }; $teams = Get-NetLbfoTeam; if (-not $teams) { 'NOT_APPLICABLE=No NIC team'; exit 0 }; foreach ($team in $teams) { 'Name=' + $team.Name; 'Status=' + $team.Status; 'Mode=' + $team.TeamingMode; 'Members=' + ((Get-NetLbfoTeamMember -Team $team.Name).Count); '' }"

```


* **정상 기준**: 생성된 NIC 팀(Teaming)의 상태가 'Up'이고, 소속된 멤버 어댑터 개수가 최소 2개 이상일 것
* **threshold key**:
* `status_ok`: "Up"
* `min_members`: 2



---

## 18. PingLoss 상태

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: PingLoss 상태
* **명령어**:
```powershell
powershell.exe -NoProfile -Command "$gw = (Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric | Select-Object -First 1 -ExpandProperty NextHop); if (-not $gw) { 'NO_DEFAULT_GATEWAY'; exit 0 }; ping -n 5 $gw"

```


* **정상 기준**: 기본 게이트웨이(Default Gateway)로의 핑 테스트 시 패킷 손실률이 0%이고, 평균 왕복 시간(RTT)이 100ms 이하일 것
* **threshold key**:
* `max_loss`: 0
* `max_avg_rtt`: 100



---

## 19. Path 이중화 상태

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: Path 이중화 상태
* **명령어**:
```powershell
powershell.exe -NoProfile -Command "$cmd = Get-Command Get-MPIOPath -ErrorAction SilentlyContinue; if (-not $cmd) { 'NOT_APPLICABLE=Get-MPIOPath unavailable'; exit 0 }; $paths = Get-MPIOPath; if (-not $paths) { 'NOT_APPLICABLE=No MPIO path'; exit 0 }; $paths | Group-Object InstanceName | ForEach-Object { 'Name=' + $_.Name; 'PathCount=' + $_.Count; 'ActivePaths=' + (($_.Group | Where-Object { $_.PathState -match 'Active|Up|Online' }).Count); 'State=' + ((($_.Group | Select-Object -ExpandProperty PathState -Unique) -join ',')); '' }"

```


* **정상 기준**: 다중 경로 I/O(MPIO) 스토리지 연결 경로 수 및 활성화 상태 정보 수집 (임계값 미지정)

---

## 20. HBA 연결상태 점검

* **도메인**: server
* **플랫폼**: windows
* **점검 항목**: HBA 연결상태 점검
* **명령어**:
```powershell
powershell.exe -NoProfile -Command "$cmd = Get-Command Get-InitiatorPort -ErrorAction SilentlyContinue; if (-not $cmd) { 'NOT_APPLICABLE=Get-InitiatorPort unavailable'; exit 0 }; $ports = Get-InitiatorPort; if (-not $ports) { 'NOT_APPLICABLE=No initiator port'; exit 0 }; foreach ($p in $ports) { 'NodeAddress=' + $p.NodeAddress; 'PortAddress=' + $p.PortAddress; 'ConnectionType=' + $p.ConnectionType; 'PortState=' + $p.PortState; '' }"

```


* **정상 기준**: 광채널 이니시에이터 포트(HBA 포트) 주소, 연결 유형 및 포트 링크 상태 정보 수집 (임계값 미지정)
