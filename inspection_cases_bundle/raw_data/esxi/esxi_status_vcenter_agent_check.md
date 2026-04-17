# 영역
클라우드

# 세부 점검항목
ESXi vCenter Agent 통신 상태 확인

# 점검 내용
vCenter와 통신하는 Agent 상태 확인

# 구분
권고

# 명령어
기본 점검은 `VMwareHelper`로 ESXi에 접속한 뒤 `HostSystem.summary`와 `HostServiceSystem` 정보를 함께 확인한다.

```python
helper = self.vmware_helper
service_instance, disconnect = helper.connect()
try:
    host = helper.select_host(service_instance, host_moid="ha-host")
    summary = host.summary
    management_server_ip = summary.managementServerIp
    connection_state = summary.runtime.connectionState
    service_system = host.configManager.serviceSystem
    services = service_system.serviceInfo.service
finally:
    disconnect(service_instance)
```

# 출력 결과
```json
{
  "host_name": "localhost.rtnet",
  "managed_by_vcenter": true,
  "management_server_ip": "192.168.1.10",
  "connection_state": "connected",
  "vpxa": {
    "exists": true,
    "running": true,
    "policy": "on"
  }
}
```

# 설명
- 이 항목은 ESXi가 vCenter에 등록되어 관리되는 환경에서 vCenter Agent 통신 상태를 확인한다.
- `vpxa`는 vCenter Agent이며 vCenter의 작업 전달, 인벤토리 갱신, 상태 보고에 사용된다.
- `summary.managementServerIp`가 있으면 해당 ESXi가 vCenter 관리 대상인지 확인할 수 있다.
- `summary.runtime.connectionState`가 `connected`이면 관리 연결 상태가 정상으로 해석된다.
- 단독 ESXi 운영 환경에서는 vCenter 관리 서버 정보가 없을 수 있으며, 이 경우 운영 정책에 따라 대상미해당으로 분류한다.
- vCenter 관리 대상인데 `vpxa`가 중지되어 있거나 `connectionState`가 `connected`가 아니면 vCenter 연동 상태 점검이 필요하다.

# 임계치
require_vcenter_connection
expected_connection_state

# 판단기준
- **양호**: vCenter 관리 대상 ESXi에서 `vpxa`가 실행 중이고 `connection_state`가 `connected`이며 관리 서버 정보가 확인되는 경우
- **경고**: vCenter 관리 대상인데 `vpxa`가 중지되어 있거나 `connection_state`가 `connected`가 아니거나 관리 서버 정보가 누락된 경우
- **대상미해당**: 단독 ESXi 운영 정책이고 vCenter 연결을 요구하지 않는 경우
- **확인 필요**: ESXi API 인증, vCenter 관리 정보 조회, Agent 상태 확인이 불가능한 경우
