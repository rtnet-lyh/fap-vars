# 영역
NETWORK

# 세부 점검 항목
커널 네트워크 파라미터

# 점검 내용
IPv4 포워딩과 Source Route 허용 여부를 조회해 보안과 라우팅 기본 설정을 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $os=Get-CimInstance Win32_OperatingSystem; $tcp=Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters' -ErrorAction SilentlyContinue; $if4=Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue; [pscustomobject]@{'kernel.osrelease'=\"$($os.Version) (Build $($os.BuildNumber))\";'kernel.ostype'=$os.Caption;'kernel.hostname'=$os.CSName;'kernel.shmmax'='N/A';'kernel.shmall'='N/A';'net.ipv4.ip_forward'=$(if($tcp.PSObject.Properties.Name -contains 'IPEnableRouter'){$tcp.IPEnableRouter}else{(@($if4.Forwarding|Select-Object -Unique)-join ',')});'net.ipv4.conf.all.rp_filter'='N/A';'net.ipv4.conf.all.accept_source_route'=$(if($tcp.PSObject.Properties.Name -contains 'DisableIPSourceRouting'){$tcp.DisableIPSourceRouting}else{'NotConfigured'});'net.core.somaxconn'='N/A';'vm.swappiness'='N/A';'vm.dirty_ratio'='N/A';'fs.file-max'=$(if($tcp.PSObject.Properties.Name -contains 'TcpNumConnections'){$tcp.TcpNumConnections}else{'N/A'});'fs.aio-max-nr'='N/A'} | Format-List
```

# 출력 결과
```text
IPEnableRouter : 0
DisableIPSourceRouting : 2
```

# 설명
- 레지스트리 기반 TCP/IP 설정을 조회해 불필요한 라우팅과 Source Route 허용 여부를 봅니다.
- 기본 사용자 단말에서는 포워딩 비활성, Source Route 차단 구성이 일반적입니다.

# 임계치
- `expected_ip_forward`: `0`
- `disallowed_accept_source_route_values`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: `IPEnableRouter`와 Source Route 관련 값이 기대한 보안 기준을 만족합니다.
- **경고**: 포워딩이 활성화되어 있거나 허용되지 않은 Source Route 값이 확인됩니다.


