# 영역
클라우드

# 세부 점검항목
ESXi Agent 상태 확인

# 점검 내용
하이퍼바이저와 해당 가상시스템을 관리하고 구성하는 Agent 상태 확인

# 구분
권고

# 명령어
기본 점검은 `inspection_runtime/items/common/helpers/vmware.py`의 `VMwareHelper`로 ESXi에 접속한 뒤 `HostServiceSystem` 서비스 목록을 조회한다.

```python
helper = self.vmware_helper
service_instance, disconnect = helper.connect()
try:
    host = helper.select_host(service_instance, host_moid="ha-host")
    service_system = host.configManager.serviceSystem
    services = service_system.serviceInfo.service
finally:
    disconnect(service_instance)
```

# 출력 결과
```json
{
  "host_name": "localhost.rtnet",
  "services": [
    {
      "key": "hostd",
      "label": "hostd",
      "running": true,
      "policy": "on"
    },
    {
      "key": "vpxa",
      "label": "vpxa",
      "running": true,
      "policy": "on"
    }
  ],
  "missing_services": [],
  "stopped_services": []
}
```

# 설명
- ESXi의 `hostd`는 Host Client, vSphere API, VM 관리 작업을 처리하는 핵심 Host Agent이다.
- `vpxa`는 vCenter Agent이며, ESXi가 vCenter에 등록되어 관리되는 환경에서 vCenter와 통신하는 데 사용된다.
- ESXi 단독 운영 환경에서는 `vpxa`가 없거나 중지되어 있어도 정책상 대상미해당일 수 있으므로 vCenter 관리 여부와 함께 해석한다.
- `HostServiceSystem.serviceInfo.service`에서 서비스 목록, 실행 여부, 시작 정책을 확인한다.
- API에서 서비스 정보가 충분히 노출되지 않는 환경은 서비스 상태를 확인할 수 없으므로 확인 필요로 분류한다.
- `hostd`가 중지되어 있으면 ESXi 관리 기능과 VM 관리 작업에 영향이 있으므로 즉시 확인이 필요하다.
- vCenter 관리 대상 ESXi에서 `vpxa`가 중지되어 있으면 vCenter 연동, 인벤토리 갱신, 작업 전달에 문제가 생길 수 있다.

# 임계치
required_agent_services
require_vpxa_when_managed

# 판단기준
- **양호**: 필수 Agent 서비스가 존재하고 `hostd`가 실행 중이며, vCenter 관리 대상인 경우 `vpxa`도 실행 중인 경우
- **경고**: `hostd`가 중지되어 있거나, vCenter 관리 대상인데 `vpxa`가 없거나 중지된 경우
- **대상미해당**: 단독 ESXi 운영 정책이고 `vpxa` 점검을 요구하지 않는 경우
- **확인 필요**: ESXi API 인증, 서비스 목록 조회, 서비스 상태 해석이 불가능한 경우
