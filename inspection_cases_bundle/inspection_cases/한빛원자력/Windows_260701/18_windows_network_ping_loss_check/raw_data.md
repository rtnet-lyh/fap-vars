# 영역
NETWORK

# 세부 점검 항목
기본 게이트웨이 Ping 품질

# 점검 내용
기본 경로의 게이트웨이를 찾아 10회 Ping을 수행하고 손실률과 평균 지연시간을 확인합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); ping -n 10 ((Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" | Sort-Object RouteMetric,InterfaceMetric | Select-Object -First 1).NextHop)
```

# 출력 결과
```text
Ping 192.168.0.1 with 32 bytes of data:
Reply from 192.168.0.1: bytes=32 time=2ms TTL=64

Packets: Sent = 10, Received = 10, Lost = 0 (0% loss)
Minimum = 1ms, Maximum = 4ms, Average = 2ms
```

# 설명
- 기본 라우팅이 정상인지와 국지적 네트워크 품질을 빠르게 확인하는 항목입니다.
- 패킷 손실률과 평균 RTT를 기준으로 판단합니다.

# 임계치
- `max_loss_percent`: `0`
  - Ping 손실률이 `0%` 이하이면 정상입니다.
  - Ping 손실률이 `0%` 초과이면 기준 미충족입니다.
- `max_average_time_ms`: `50`
  - 평균 응답 시간이 `50ms` 이하이면 정상입니다.
  - 평균 응답 시간이 `50ms` 초과이면 기준 미충족입니다.
- `failure_keywords`: 없음
  - 실패 키워드가 설정되면 Ping 원문 출력에 해당 키워드가 포함될 때 기준 미충족입니다.

# 판단기준
- **정상**: 손실률이 낮고 평균 응답시간이 임계치 이하입니다.
- **경고**: 손실률 또는 평균 응답시간이 임계치를 초과합니다.


