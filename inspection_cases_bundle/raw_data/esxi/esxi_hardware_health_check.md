# 영역
클라우드

# 세부 점검항목
ESXi 하드웨어 Health 상태 확인

# 점검 내용
ESXi 하드웨어 및 HA 대체 상태 확인

# 구분
권고

# 명령어
기본 점검은 `VMwareHelper`로 ESXi에 접속한 뒤 `HostSystem.summary.overallStatus`와 하드웨어 Health Runtime 정보를 조회한다.

```python
helper = self.vmware_helper
service_instance, disconnect = helper.connect()
try:
    host = helper.select_host(service_instance, host_moid="ha-host")
    summary = host.summary
    runtime = host.runtime
    health_info = runtime.healthSystemRuntime.systemHealthInfo
finally:
    disconnect(service_instance)
```

ESXi Shell 보조 확인이 필요한 경우 다음 명령 출력과 교차 확인한다.

```sh
esxcli hardware status system ha summary get
```

# 출력 결과
```json
{
  "host_name": "localhost.rtnet",
  "overall_status": "green",
  "hardware_health": {
    "power_supply": "Normal",
    "fan": "Normal",
    "temperature": "Normal",
    "voltage": "Normal",
    "battery": "Normal"
  },
  "warning_sensors": [],
  "failed_sensors": []
}
```

# 설명
- vSphere HA 클러스터 구성 상태는 vCenter Cluster 기능이므로 ESXi 단독 점검에서는 완전하게 판정할 수 없다.
- ESXi 직접 점검에서는 하드웨어 Health와 Host overall status를 확인하는 항목으로 재정의한다.
- `summary.overallStatus`는 Host의 전반 상태를 나타내며 `green`이면 정상, `yellow`나 `red`이면 점검이 필요하다.
- `runtime.healthSystemRuntime.systemHealthInfo`에서 전원 공급 장치, 팬, 온도, 전압, 배터리 등 하드웨어 센서 상태를 확인한다.
- 일부 장비나 라이선스/드라이버 환경에서는 센서 정보가 제한적으로 노출될 수 있으므로 벤더 관리도구 결과와 교차 확인한다.
- 매뉴얼의 `Overall Status`, `Power Supply`, `Fan`, `Temperature`, `Voltage`, `Battery` 기준을 ESXi API에서 확인 가능한 Health 정보로 대응한다.

# 임계치
expected_overall_status
normal_health_states

# 판단기준
- **양호**: `overall_status`가 `green`이고 주요 하드웨어 센서 상태가 `Normal` 또는 운영 기준상 정상 상태인 경우
- **경고**: `overall_status`가 `yellow` 또는 `red`이거나 Power/Fan/Temperature/Voltage/Battery 중 Warning, Failure, Unknown 상태가 확인되는 경우
- **확인 필요**: ESXi API 인증, 하드웨어 Health 정보 조회, 센서 상태 해석이 불가능한 경우
