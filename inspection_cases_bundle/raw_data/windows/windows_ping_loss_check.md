# 영역
NETWORK

# 세부 점검항목
Ping Loss

# 점검 내용
기본 게이트웨이 대상 Ping 손실률 확인

# 구분
권고

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $target = (Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric | Select-Object -First 1).NextHop; if (-not $target) { $target = '127.0.0.1' }; $count = 4; $ok = @(Test-Connection -ComputerName $target -Count $count -Quiet:$false -ErrorAction SilentlyContinue); $success = @($ok).Count; [pscustomobject]@{ target = $target; sent_count = $count; success_count = $success; loss_percent = [math]::Round((($count - $success) / $count) * 100, 2) } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"target":"192.168.1.1","sent_count":4,"success_count":4,"loss_percent":0.0}
```

# 설명
- 기본 라우트의 NextHop을 대상으로 Test-Connection을 수행해 손실률을 계산한다.
- 손실률이 임계치를 초과하면 네트워크 경로, 게이트웨이, 방화벽, NIC 상태를 확인한다.

# 임계치
max_ping_loss_percent: 0

# 판단기준
- **양호**: Ping 손실률이 임계치 이하인 경우
- **경고**: Ping 손실률이 임계치를 초과한 경우
