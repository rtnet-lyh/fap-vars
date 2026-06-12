# 영역
클라우드

# 세부 점검항목
ESXi 하드웨어 Health 상태 확인

# 점검 내용
ESXi 하드웨어 및 HA 대체 상태 확인

# 구분
권고

# 명령어
기본 점검은 `VMwareHelper.hardware_health_from_context()`를 사용한다. 실제 접속 정보의 `password`가 있으면 pyVmomi로 ESXi에 접속해 `HostSystem.summary.overallStatus`와 하드웨어 Health Runtime 정보를 조회하고, `password`가 없거나 `force_replay=true`이면 `outputs/hardware_health.json` fixture를 읽어 같은 metrics로 판정한다.

```python
helper = self.vmware_helper
metrics = helper.hardware_health_from_context(
    default_host_moid="ha-host",
    source="pyvmomi",
)
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
- 센서 정보가 비어 있고 `overall_status`도 기대값과 다르면 정책 실패로 분류한다. 센서가 제한적으로 노출되는 장비는 벤더 관리도구 또는 vCenter Health 정보와 함께 해석한다.
- output fixture 처리는 공통 `VMwareHelper`가 담당하며 개별 `script.py`에서는 fixture 파일을 직접 읽지 않는다.
- 매뉴얼의 `Overall Status`, `Power Supply`, `Fan`, `Temperature`, `Voltage`, `Battery` 기준을 ESXi API에서 확인 가능한 Health 정보로 대응한다.

# 임계치
expected_overall_status
normal_health_states
force_replay

# 판단기준
- **양호**: `overall_status`가 `green`이고 주요 하드웨어 센서 상태가 `Normal` 또는 운영 기준상 정상 상태인 경우
- **경고**: `overall_status`가 기대값이 아니거나 Power/Fan/Temperature/Voltage/Battery 중 Warning, Failure, Unknown 상태가 확인되는 경우
- **확인 필요**: ESXi API 인증, 하드웨어 Health 정보 조회, 센서 상태 해석이 불가능한 경우
