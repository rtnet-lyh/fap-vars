# 영역
클라우드

# 세부 점검항목
ESXi Agent 상태 확인

# 점검 내용
하이퍼바이저와 해당 가상시스템을 관리하고 구성하는 Agent 상태 확인

# 구분
권고

# 명령어
기본 점검은 `inspection_runtime/items/common/helpers/vmware.py`의 `VMwareHelper.agent_services_from_context()`를 사용한다. 실제 접속 정보의 `password`가 있으면 pyVmomi로 ESXi에 접속해 `HostServiceSystem` 서비스 목록을 조회하고, `password`가 없거나 `force_replay=true`이면 `outputs/agent_services.json` fixture를 읽어 같은 metrics로 판정한다.

```python
helper = self.vmware_helper
metrics = helper.agent_services_from_context(
    default_host_moid="ha-host",
    source="pyvmomi",
)
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
- 일부 ESXi API 응답에서 `hostd`가 서비스 목록에 직접 노출되지 않을 수 있다. 이 경우 vSphere API 세션 자체가 `hostd`를 통해 성립하므로 공통 `VMwareHelper`가 `hostd (vSphere API session)` 항목을 실행 중으로 보정한다.
- output fixture 처리는 공통 `VMwareHelper`가 담당하며 개별 `script.py`에서는 fixture 파일을 직접 읽지 않는다.
- API에서 서비스 정보가 충분히 노출되지 않는 환경은 서비스 상태를 확인할 수 없으므로 확인 필요로 분류한다.
- `hostd`가 중지되어 있으면 ESXi 관리 기능과 VM 관리 작업에 영향이 있으므로 즉시 확인이 필요하다.
- vCenter 관리 대상 ESXi에서 `vpxa`가 중지되어 있으면 vCenter 연동, 인벤토리 갱신, 작업 전달에 문제가 생길 수 있다.

# 임계치
required_agent_services
require_vpxa_when_managed
force_replay

# 판단기준
- **양호**: 필수 Agent 서비스가 존재하고 `hostd`가 실행 중이며, vCenter 관리 대상인 경우 `vpxa`도 실행 중인 경우
- **경고**: `hostd`가 없거나 중지되어 있거나, vCenter 관리 대상인데 `vpxa`가 없거나 중지된 경우
- **대상미해당**: 단독 ESXi 운영 정책이고 `vpxa` 점검을 요구하지 않는 경우. 기본 구현에서는 vCenter 관리 대상이 아닐 때 `vpxa`를 요구하지 않는다.
- **확인 필요**: ESXi API 인증, 서비스 목록 조회, 서비스 상태 해석이 불가능한 경우
