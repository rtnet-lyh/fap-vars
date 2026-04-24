# 영역
클라우드

# 세부 점검항목
ESXi vCenter Agent 통신 상태 확인

# 점검 내용
vCenter와 통신하는 Agent 상태 확인

# 구분
권고

# 명령어
기본 점검은 `VMwareHelper.vcenter_agent_status_from_context()`를 사용한다. 실제 접속 정보의 `password`가 있으면 pyVmomi로 ESXi에 접속해 `HostSystem.summary`와 `HostServiceSystem` 정보를 함께 확인하고, `password`가 없거나 `force_replay=true`이면 `outputs/vcenter_agent.json` fixture를 읽어 같은 metrics로 판정한다.

```python
helper = self.vmware_helper
metrics = helper.vcenter_agent_status_from_context(
    default_host_moid="ha-host",
    source="pyvmomi",
)
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
- 단독 ESXi 운영 환경에서는 vCenter 관리 서버 정보가 없을 수 있으며, 기본 구현은 `require_vcenter_connection=false`로 두어 이 경우 대상미해당 성격의 `warn`으로 분류한다.
- vCenter 연결을 필수로 운영하는 환경에서는 `require_vcenter_connection=true`로 설정해 관리 서버 정보, 연결 상태, `vpxa` 상태를 모두 필수 기준으로 판정한다.
- output fixture 처리는 공통 `VMwareHelper`가 담당하며 개별 `script.py`에서는 fixture 파일을 직접 읽지 않는다.
- vCenter 관리 대상인데 `vpxa`가 중지되어 있거나 `connectionState`가 `connected`가 아니면 vCenter 연동 상태 점검이 필요하다.

# 임계치
require_vcenter_connection
expected_connection_state
force_replay

# 판단기준
- **양호**: vCenter 관리 대상 ESXi에서 `vpxa`가 실행 중이고 `connection_state`가 `connected`이며 관리 서버 정보가 확인되는 경우
- **경고**: vCenter 관리 대상인데 `vpxa`가 중지되어 있거나 `connection_state`가 `connected`가 아니거나 관리 서버 정보가 누락된 경우
- **대상미해당**: 단독 ESXi 운영 정책이고 `require_vcenter_connection=false`로 vCenter 연결을 요구하지 않는 경우
- **확인 필요**: ESXi API 인증, vCenter 관리 정보 조회, Agent 상태 확인이 불가능한 경우
